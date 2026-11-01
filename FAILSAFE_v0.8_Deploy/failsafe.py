"""FAILSAFE v0.1 — synthetic patient-journey stress-testing prototype.

Only Python's standard library is required. All probabilities are explicitly
invented for a software demonstration; they are NOT clinically validated.
No real patient data is loaded, and outputs must not be used for care decisions.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import random
from typing import Literal

Stage = Literal["handoff", "instructions", "medication", "booking", "attendance"]
STAGES: tuple[Stage, ...] = (
    "handoff", "instructions", "medication", "booking", "attendance"
)
SCENARIOS = ("baseline", "teachback", "medication_support", "followup_support", "all")

# These are deliberately hypothetical choices, NOT estimates from published research.
# The same patient's random draws are reused across scenarios, making a paired
# counterfactual comparison rather than comparing two unrelated synthetic cohorts.
TRAIT_FREQUENCIES = {
    "interpreter_needed": 0.18,
    "health_literacy_support_needed": 0.22,
    "medication_access_barrier": 0.20,
    "transport_barrier": 0.16,
    "limited_digital_access": 0.18,
    "complex_discharge": 0.28,
}


@dataclass(frozen=True)
class Patient:
    patient_id: int
    interpreter_needed: bool
    health_literacy_support_needed: bool
    medication_access_barrier: bool
    transport_barrier: bool
    limited_digital_access: bool
    complex_discharge: bool


@dataclass(frozen=True)
class Interventions:
    teachback_and_interpreter: bool = False
    medication_navigation: bool = False
    followup_coordination: bool = False


INTERVENTIONS = {
    "baseline": Interventions(),
    "teachback": Interventions(teachback_and_interpreter=True),
    "medication_support": Interventions(medication_navigation=True),
    "followup_support": Interventions(followup_coordination=True),
    "all": Interventions(True, True, True),
}


@dataclass(frozen=True)
class PatientJourney:
    patient: Patient
    scenario: str
    handoff: str
    instructions: str
    medication: str
    booking: str
    attendance: str
    fully_completed: bool

    def status(self, stage: Stage) -> str:
        return getattr(self, stage)


def generate_patients(
    count: int, seed: int, trait_frequencies: dict[str, float] | None = None
) -> list[Patient]:
    """Generate a reproducible cohort with explicitly hypothetical trait rates."""
    if count < 1:
        raise ValueError("Number of patients must be at least 1")
    frequencies = dict(TRAIT_FREQUENCIES)
    if trait_frequencies is not None:
        unknown = set(trait_frequencies) - set(frequencies)
        if unknown:
            raise ValueError(f"Unknown synthetic trait(s): {', '.join(sorted(unknown))}")
        for key, value in trait_frequencies.items():
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not (0 <= value <= 1)):
                raise ValueError(f"Synthetic frequency for {key} must be between 0 and 1")
            frequencies[key] = float(value)
    rng = random.Random(seed)
    return [
        Patient(
            patient_id=i + 1,
            **{key: rng.random() < value for key, value in frequencies.items()},
        )
        for i in range(count)
    ]

def stable_draw(seed: int, patient_id: int, stage: Stage) -> float:
    """Stable, scenario-independent uniform draw per patient and checkpoint."""
    digest = sha256(f"failsafe-v1:{seed}:{patient_id}:{stage}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def stage_probability(stage: Stage, p: Patient, interventions: Interventions) -> float:
    """Illustrative event rules; tune/validate later using real research."""
    if stage == "handoff":
        probability = 0.96 - 0.09 * p.complex_discharge
    elif stage == "instructions":
        probability = (0.91
                       - 0.27 * p.interpreter_needed
                       - 0.14 * p.health_literacy_support_needed
                       - 0.06 * p.complex_discharge)
        if interventions.teachback_and_interpreter:
            probability += (0.05 + 0.24 * p.interpreter_needed
                            + 0.11 * p.health_literacy_support_needed)
    elif stage == "medication":
        probability = (0.92
                       - 0.27 * p.medication_access_barrier
                       - 0.07 * p.complex_discharge)
        if interventions.medication_navigation:
            probability += 0.04 + 0.23 * p.medication_access_barrier
    elif stage == "booking":
        probability = (0.92
                       - 0.16 * p.limited_digital_access
                       - 0.06 * p.complex_discharge)
        if interventions.followup_coordination:
            probability += 0.05 + 0.16 * p.limited_digital_access
    elif stage == "attendance":
        probability = (0.93
                       - 0.25 * p.transport_barrier
                       - 0.07 * p.limited_digital_access
                       - 0.04 * p.complex_discharge)
        if interventions.followup_coordination:
            probability += (0.04 + 0.15 * p.transport_barrier
                            + 0.04 * p.limited_digital_access)
    else:
        raise ValueError(f"Unknown checkpoint: {stage}")
    return min(0.99, max(0.01, probability))


def simulate_patient(
    p: Patient, seed: int, scenario: str, *, interventions: Interventions | None = None
) -> PatientJourney:
    """Run one journey; optionally provide flags for a custom intervention mix."""
    if interventions is None and scenario not in INTERVENTIONS:
        raise ValueError(f"Unknown scenario: {scenario}")
    flags = INTERVENTIONS[scenario] if interventions is None else interventions

    def result(stage: Stage) -> str:
        return ("pass" if stable_draw(seed, p.patient_id, stage)
                < stage_probability(stage, p, flags) else "fail")

    handoff = result("handoff")
    if handoff == "fail":
        # Prevent double-counting downstream steps as separate failures.
        instructions = medication = booking = attendance = "blocked"
    else:
        instructions = result("instructions")
        medication = result("medication")
        booking = result("booking")
        attendance = result("attendance") if booking == "pass" else "blocked"

    steps = (handoff, instructions, medication, booking, attendance)
    return PatientJourney(
        patient=p,
        scenario=scenario,
        handoff=handoff,
        instructions=instructions,
        medication=medication,
        booking=booking,
        attendance=attendance,
        fully_completed=all(status == "pass" for status in steps),
    )


def simulate(
    cohort: list[Patient], seed: int, scenario: str,
    *, interventions: Interventions | None = None
) -> list[PatientJourney]:
    return [simulate_patient(p, seed, scenario, interventions=interventions) for p in cohort]


def summarize(rows: list[PatientJourney]) -> dict:
    count = len(rows)
    if not count:
        raise ValueError("Cannot summarize an empty cohort")
    completed = sum(r.fully_completed for r in rows)
    failures = {stage: sum(r.status(stage) == "fail" for r in rows) for stage in STAGES}
    blocked = {stage: sum(r.status(stage) == "blocked" for r in rows) for stage in STAGES}
    return {
        "patients": count,
        "fully_completed": completed,
        "completion_pct": round(completed * 100 / count, 1),
        "patients_with_one_or_more_failures": count - completed,
        "failed_checkpoints": failures,
        "blocked_checkpoints": blocked,
        "total_failed_events": sum(failures.values()),
    }


def write_csv(path: Path, rows: list[PatientJourney]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "patient_id", "scenario", *TRAIT_FREQUENCIES.keys(),
            *STAGES, "fully_completed", "first_failed_checkpoint"
        ])
        for r in rows:
            first_failed = next((stage for stage in STAGES if r.status(stage) == "fail"), "")
            writer.writerow([
                r.patient.patient_id, r.scenario,
                *(int(getattr(r.patient, key)) for key in TRAIT_FREQUENCIES),
                *(r.status(stage) for stage in STAGES),
                int(r.fully_completed), first_failed,
            ])


def run(count: int = 500, seed: int = 42, out: str | Path = "failsafe_output") -> dict:
    """Run and export paired experiments with the SAME cohort and random draws."""
    cohort = generate_patients(count, seed)
    destination = Path(out)
    destination.mkdir(parents=True, exist_ok=True)
    results: dict = {
        "warning": "SYNTHETIC SOFTWARE DEMO ONLY — probabilities are hypothetical, not clinical evidence.",
        "study": "Five-checkpoint hospital-to-home transition, with hypothetical assumptions.",
        "seed": seed,
        "synthetic_trait_frequencies": TRAIT_FREQUENCIES,
        "scenarios": {},
    }
    for scenario in SCENARIOS:
        journeys = simulate(cohort, seed, scenario)
        results["scenarios"][scenario] = summarize(journeys)
        write_csv(destination / f"{scenario}.csv", journeys)

    baseline = results["scenarios"]["baseline"]["fully_completed"]
    results["paired_difference_vs_baseline"] = {
        name: {
            "additional_completed": details["fully_completed"] - baseline,
            "percentage_point_change": round(
                (details["fully_completed"] - baseline) * 100 / count, 1
            ),
        }
        for name, details in results["scenarios"].items() if name != "baseline"
    }
    with (destination / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)

    print("\nFAILSAFE v0.1 — SYNTHETIC PATIENT-JOURNEY SIMULATION")
    print("DISCLAIMER: Fictional probabilities; NOT validated medical predictions.\n")
    print(f"Cohort: {count} fictitious patients | Seed: {seed}")
    print("-" * 67)
    print(f"{'Scenario':<23} {'Completed':>13} {'Rate':>10} {'Δ vs base':>15}")
    print("-" * 67)
    for name, details in results["scenarios"].items():
        change = details["fully_completed"] - baseline
        print(f"{name:<23} {details['fully_completed']:>6} / {count:<6}"
              f" {details['completion_pct']:>8.1f}% {change:>+10} patients")
    print("\nBaseline failed checkpoints (each event counted separately):")
    for stage, failures in results["scenarios"]["baseline"]["failed_checkpoints"].items():
        blocked = results["scenarios"]["baseline"]["blocked_checkpoints"][stage]
        print(f"  {stage:<14} {failures:>3} failed; {blocked:>3} blocked")
    print(f"\nSaved patient-level CSVs and summary.json in: {destination.resolve()}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="FAILSAFE synthetic patient pathway MVP")
    parser.add_argument("--patients", type=int, default=500, help="Fictitious patient count (default: 500)")
    parser.add_argument("--seed", type=int, default=42, help="Reproducible random seed (default: 42)")
    parser.add_argument("--out", type=Path, default=Path("failsafe_output"), help="Output directory")
    args = parser.parse_args()
    if args.patients < 1:
        parser.error("--patients must be at least 1")
    run(args.patients, args.seed, args.out)


if __name__ == "__main__":
    main()
