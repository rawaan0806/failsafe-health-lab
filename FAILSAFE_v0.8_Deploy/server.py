"""FAILSAFE v0.7 website and v0.6 local simulation API. No real patient data."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from failsafe import STAGES, TRAIT_FREQUENCIES
from optimizer import evaluate
from capacity import capacity_run
from joint_optimizer import optimize_joint

ROOT = Path(__file__).resolve().parent
MAX_BODY = 16_384


def parse_config(raw: dict) -> dict:
    """Validate every user-controlled parameter (API boundary)."""
    if not isinstance(raw, dict):
        raise ValueError("The request must be a JSON object")
    allowed = {"patients", "seed", "budget", "validation_seeds", "trait_percentages", "capacity", "completion_weight"}
    unexpected = set(raw) - allowed
    if unexpected:
        raise ValueError(f"Unknown parameter: {sorted(unexpected)[0]}")

    def integer(name: str, default: int, lower: int, upper: int) -> int:
        val = raw.get(name, default)
        if type(val) is not int or not lower <= val <= upper:
            raise ValueError(f"{name} must be an integer from {lower} to {upper}")
        return val

    patients = integer("patients", 500, 50, 1500)
    completion_weight = integer("completion_weight", 60, 0, 100)
    seed = integer("seed", 42, 0, 10_000_000)
    validation_seeds = integer("validation_seeds", 5, 1, 8)
    budget = raw.get("budget", 350)
    if (type(budget) not in (int, float) or not 0 <= budget <= 2500):
        raise ValueError("budget must be a number from 0 to 2500")
    raw_rates = raw.get("trait_percentages", {})
    if not isinstance(raw_rates, dict):
        raise ValueError("trait_percentages must be an object")
    unknown_rates = set(raw_rates) - set(TRAIT_FREQUENCIES)
    if unknown_rates:
        raise ValueError(f"Unknown trait: {sorted(unknown_rates)[0]}")
    rates = dict(TRAIT_FREQUENCIES)
    for key, percent in raw_rates.items():
        if type(percent) not in (int, float) or not 0 <= percent <= 100:
            raise ValueError(f"Trait {key} must be a percentage from 0 to 100")
        rates[key] = percent / 100
    raw_cap = raw.get("capacity", {})
    if not isinstance(raw_cap, dict):
        raise ValueError("capacity must be an object")
    limits = {"discharge_staff": (3,1,30), "booking_staff": (2,1,30),
              "arrivals_per_day": (80,10,500), "service_minutes": (18,5,90),
              "booking_minutes": (12,5,90)}
    if set(raw_cap)-set(limits):
        raise ValueError("Unknown capacity parameter")
    cap = {}
    for key,(default,lo,hi) in limits.items():
        value = raw_cap.get(key,default)
        if type(value) is not int or not lo <= value <= hi:
            raise ValueError(f"{key} must be an integer from {lo} to {hi}")
        cap[key] = value
    return {
        "capacity": cap,
        "completion_weight": completion_weight,
        "patients": patients,
        "seed": seed,
        "budget": float(budget),
        "validation_seeds": validation_seeds,
        "trait_frequencies": rates,
    }


def calculate_trace(raw: dict) -> dict:
    """Replay exactly the same event schedule used by the queue metrics.

    The trace is for operational staffing only; care-pathway outcomes come
    from a separate independent model. The UI must not mix the two.
    """
    if not isinstance(raw, dict) or set(raw) != {'config', 'added_discharge_staff', 'added_booking_staff'}:
        raise ValueError('Trace expects config and two staffing additions')
    config = parse_config(raw['config'])
    extras = []
    for k in ('added_discharge_staff', 'added_booking_staff'):
        v = raw[k]
        if type(v) is not int or v not in (0, 1, 2):
            raise ValueError(f'{k} must be 0, 1, or 2')
        extras.append(v)
    cap = {**config['capacity']}
    cap['discharge_staff'] += extras[0]
    cap['booking_staff'] += extras[1]
    if cap['discharge_staff'] > 30 or cap['booking_staff'] > 30:
        raise ValueError('Total staff cannot exceed 30 per service station')
    simulated = capacity_run(config['patients'], config['seed'], **cap, include_trace=True)
    return {'version':'0.6', 'synthetic_only':True, 'queue':simulated,
            'staffing': {'discharge_staff':cap['discharge_staff'], 'booking_staff':cap['booking_staff']},
            'note': 'Operational queue event trace only. No actual patients or health predictions.'}


def calculate(raw: dict) -> dict:
    config = parse_config(raw)
    audit, runs = evaluate(
        patients=config["patients"],
        seed=config["seed"],
        budget=config["budget"],
        validation_seeds=config["validation_seeds"],
        trait_frequencies=config["trait_frequencies"],
    )
    joint = optimize_joint(audit, config["patients"], config["seed"],
                           config["capacity"], config["budget"],
                           config["validation_seeds"], config["completion_weight"])
    capacity_result = capacity_run(config["patients"], config["seed"], **config["capacity"])
    # Replication sensitivity: 5 independent deterministic arrival/service draws.
    capacity_reps = [capacity_run(config["patients"], config["seed"] + s * 31,
                      **config["capacity"]) for s in range(5)]
    capacity_result["replicated_mean_wait_range"] = [
        min(r["mean_wait_minutes"] for r in capacity_reps),
        max(r["mean_wait_minutes"] for r in capacity_reps)]
    capacity_result["assumptions"] = "Two FIFO staffing queues, fixed 8-hour modeled shifts; synthetic arrivals and service times, illustrative only. Waiting is operational, not clinical risk."
    # Status payload for a local, in-memory synthetic cohort; no persistence.
    patient_records = {}
    for plan_id, journeys in runs.items():
        patient_records[plan_id] = [
            [
                row.patient.patient_id,
                [int(getattr(row.patient, t)) for t in TRAIT_FREQUENCIES],
                [row.status(s) for s in STAGES],
                int(row.fully_completed),
            ] for row in journeys
        ]
    return {
        "version": "0.6",
        "joint_optimizer": joint,
        "capacity": capacity_result,
        "synthetic_only": True,
        "config": {**config, "trait_percentages": {
            k: round(v * 100, 2) for k, v in config["trait_frequencies"].items()
        }},
        "result": audit,
        "patient_records": patient_records,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "FAILSAFE/0.6"

    def respond(self, code: int, content: bytes, mimetype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", mimetype)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(content)

    def json_response(self, code: int, item: dict) -> None:
        self.respond(code, json.dumps(item, allow_nan=False).encode("utf-8"),
                     "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        public_files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/lab": ("lab.html", "text/html; charset=utf-8"),
            "/lab.html": ("lab.html", "text/html; charset=utf-8"),
            "/assets/styles.css": ("assets/styles.css", "text/css; charset=utf-8"),
            "/assets/home.js": ("assets/home.js", "text/javascript; charset=utf-8"),
            "/assets/favicon.svg": ("assets/favicon.svg", "image/svg+xml"),
            "/assets/simulation-screenshot.webp": ("assets/simulation-screenshot.webp", "image/webp"),
        }
        if path in public_files:
            name, mime = public_files[path]
            self.respond(200, (ROOT / name).read_bytes(), mime)
        elif path == "/health":
            self.json_response(200, {"ok": True, "version": "0.6"})
        elif path == "/favicon.ico":
            self.respond(204, b"", "image/png")
        else:
            self.json_response(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if urlsplit(self.path).path not in ("/api/simulate", "/api/trace"):
            self.json_response(404, {"error": "Not found"})
            return
        try:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                raise ValueError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", "-1"))
            if not (0 <= length <= MAX_BODY):
                raise ValueError("Request is missing or too large")
            raw = json.loads(self.rfile.read(length))
            result = calculate_trace(raw) if urlsplit(self.path).path == "/api/trace" else calculate(raw)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.json_response(400, {"error": str(exc)})
            return
        self.json_response(200, result)


def main() -> None:
    host, port = "127.0.0.1", 8765
    print("\n  FAILSAFE v0.7 — WEBSITE + LIVE LAB")
    print("  Fictional patient journeys / NOT for healthcare decisions")
    print(f"  Homepage: http://{host}:{port}")
    print(f"  Simulation lab: http://{host}:{port}/lab")
    print("  Press Ctrl+C to stop. All calculations stay on this computer.\n")
    with ThreadingHTTPServer((host, port), Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nFAILSAFE stopped.")


if __name__ == "__main__":
    main()
