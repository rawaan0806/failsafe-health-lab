"""FAILSAFE v0.2: exhaustive, explainable optimization of synthetic care interventions.

This is a *combinatorial search algorithm*, not a trained machine-learning
model. Cost units, event probabilities, and benefits are hypothetical. The
output MUST NOT be interpreted as actual healthcare effectiveness or spend.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from statistics import mean

from failsafe import (
    STAGES, TRAIT_FREQUENCIES, Interventions, PatientJourney,
    generate_patients, simulate, summarize, write_csv,
)

# Fictional resource credits per 100 patients. None of these are actual prices.
INTERVENTION_SPECS = {
    "teachback_and_interpreter": {
        "name": "Teach-back + interpreter support",
        "credits_per_100_patients": 35,
        "description": "Repeat key discharge instructions in plain language and provide an interpreter.",
    },
    "medication_navigation": {
        "name": "Medication navigation",
        "credits_per_100_patients": 30,
        "description": "Help patients obtain medicines and resolve access problems before leaving.",
    },
    "followup_coordination": {
        "name": "Follow-up coordination",
        "credits_per_100_patients": 40,
        "description": "Arrange follow-up visits proactively and address practical attendance barriers.",
    },
}
KEYS = tuple(INTERVENTION_SPECS)


def plans() -> list[tuple[str, Interventions, tuple[str, ...]]]:
    """The complete set of 2^3 possible binary intervention combinations."""
    combinations = []
    for chosen in itertools.product((False, True), repeat=len(KEYS)):
        enabled = tuple(key for key, checked in zip(KEYS, chosen) if checked)
        name = "+".join(enabled) if enabled else "baseline"
        combos = Interventions(**dict(zip(KEYS, chosen)))
        combinations.append((name, combos, enabled))
    return combinations


def credits_for(enabled: tuple[str, ...], patient_count: int) -> float:
    """Illustrative credits, linearly scaled with cohort size."""
    if patient_count < 1:
        raise ValueError("Number of patients must be positive")
    # Round up to one decimal credit; no external costs implied.
    return int(sum(INTERVENTION_SPECS[key]["credits_per_100_patients"]
                   * patient_count / 100 for key in enabled) * 10 + 0.5) / 10


def cohort_subgroups(journeys: list[PatientJourney]) -> dict:
    """Transparent descriptive counts; never infer clinical fairness from this."""
    result = {}
    for trait in TRAIT_FREQUENCIES:
        subset = [r for r in journeys if getattr(r.patient, trait)]
        result[trait] = {
            "n": len(subset),
            "completed": sum(r.fully_completed for r in subset),
            "completion_pct": round(100 * sum(r.fully_completed for r in subset) / len(subset), 1)
                if subset else None,
        }
    return result


def evaluate(patients: int = 500, seed: int = 42, budget: float = 350,
             validation_seeds: int = 5,
             trait_frequencies: dict[str, float] | None = None) -> tuple[dict, dict[str, list[PatientJourney]]]:
    if patients < 1:
        raise ValueError("At least one patient is required")
    if budget < 0:
        raise ValueError("Budget cannot be negative")
    if validation_seeds < 1 or validation_seeds > 100:
        raise ValueError("validation_seeds must be between 1 and 100")

    named_plans = plans()
    main_cohort = generate_patients(patients, seed, trait_frequencies)
    main_runs = {name: simulate(main_cohort, seed, name, interventions=flags)
                 for name, flags, _ in named_plans}
    main_baseline = summarize(main_runs["baseline"])["fully_completed"]

    # Repeat on independent synthetic cohorts; report the range so results do
    # not depend silently on one seed. Same seeds across all plans are paired.
    replications = {}
    for replicate_seed in range(seed, seed + validation_seeds):
        cohort = generate_patients(patients, replicate_seed, trait_frequencies)
        replications[replicate_seed] = {
            name: sum(j.fully_completed for j in simulate(cohort, replicate_seed,
                              name, interventions=flags))
            for name, flags, _ in named_plans
        }
    entries = []
    for name, _flags, enabled in named_plans:
        overview = summarize(main_runs[name])
        sample = [replications[s][name] for s in replications]
        baselines = [replications[s]["baseline"] for s in replications]
        deltas = [x-b for x, b in zip(sample, baselines)]
        entries.append({
            "id": name,
            "interventions": list(enabled),
            "labels": [INTERVENTION_SPECS[key]["name"] for key in enabled],
            "cost_credits": credits_for(enabled, patients),
            "demo": overview,
            "additional_completed": overview["fully_completed"] - main_baseline,
            "subgroups": cohort_subgroups(main_runs[name]),
            "validation": {
                "seeds": list(replications),
                "mean_completed": round(mean(sample), 2),
                "mean_completion_pct": round(mean(sample)*100/patients, 2),
                "min_completion_pct": round(min(sample)*100/patients, 2),
                "max_completion_pct": round(max(sample)*100/patients, 2),
                "mean_additional_completed_vs_baseline": round(mean(deltas), 2),
            }
        })

    feasible = [r for r in entries if r["cost_credits"] <= budget + 1e-9]
    # Fully exhaustive search: highest MEAN synthetic completions under budget;
    # tie-break on cost, then use stable ID. For the current three binary choices,
    # exact search is clearer and stronger than adding stochastic ML theater.
    winner = sorted(feasible, key=lambda r: (
        -r["validation"]["mean_completed"], r["cost_credits"], r["id"]
    ))[0]
    baseline = next(r for r in entries if r["id"] == "baseline")
    audit = {
        "program": "FAILSAFE v0.2 — EXPLAINABLE COMBINATORIAL SEARCH",
        "disclaimer": "Entirely hypothetical simulation. Not validated clinical performance, not actual prices, not medical advice.",
        "cohort_size": patients,
        "seed": seed,
        "synthetic_trait_frequencies": {**TRAIT_FREQUENCIES, **(trait_frequencies or {})},
        "validation_repetitions": validation_seeds,
        "budget_credits": budget,
        "cost_unit": "fictional resource credits per 100 synthetic patients",
        "cost_assumptions": INTERVENTION_SPECS,
        "objective": "Maximize mean completed synthetic 5-step journeys over paired seeds, subject to resource budget; tie-break on lowest resource cost.",
        "method": "Exact exhaustive combinatorial search of all 8 binary combinations (not a trained ML model).",
        "plans_searched": len(entries),
        "feasible_plans": len(feasible),
        "baseline": baseline["id"],
        "recommended_plan_id": winner["id"],
        "recommended_plan": winner,
        "possible_plans": entries,
        "limitations": [
            "All checkpoint probabilities, trait frequencies, effects, and intervention costs are illustrative guesses.",
            "An intervention is modeled as always beneficial; real interventions may have side effects, staffing trade-offs or interactions.",
            "This model lacks real capacity limits, waiting queues, and time-dependent medical outcomes.",
            "This is algorithmic optimization, not machine-learning training, medical prediction, or causal evidence.",
            "Protected group equity and real-world generalization cannot be assessed using synthetic inputs alone."
        ]
    }
    return audit, main_runs


def export_result(out: Path, result: dict,
                  runs: dict[str, list[PatientJourney]]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out/"optimization.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for name, rows in runs.items():
        write_csv(out/f"{name}.csv", rows)


def main():
    parser = argparse.ArgumentParser(description="FAILSAFE synthetic intervention optimizer (no clinical validation)")
    parser.add_argument("--patients", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget", type=float, default=350,
                        help="Fictional resource credits for whole simulated cohort (default: 350)")
    parser.add_argument("--validation-seeds", type=int, default=5)
    parser.add_argument("--out", type=Path, default=Path("optimizer_output"))
    args = parser.parse_args()
    try:
        result, runs = evaluate(args.patients, args.seed, args.budget, args.validation_seeds)
    except ValueError as exc:
        parser.error(str(exc))
    export_result(args.out, result, runs)
    recommended = result["recommended_plan"]
    print("\nFAILSAFE v0.2 — RESOURCE-CONSTRAINED SEARCH (SYNTHETIC ONLY)")
    print("WARNING: probabilities and costs are fictional. No clinical inference.\n")
    print(f"Checked all {result['plans_searched']} combinations; {result['feasible_plans']} within budget {args.budget:g} credits")
    print(f"Recommended: {', '.join(recommended['labels']) or 'No additional intervention'}")
    print(f"Fictional cost: {recommended['cost_credits']} credits")
    print(f"Demo completed: {recommended['demo']['fully_completed']} / {args.patients}")
    print(f"Across {args.validation_seeds} replicated synthetic cohorts: "
          f"{recommended['validation']['mean_completion_pct']:.2f}% mean completion")
    print(f"Saved audit + patient records under {args.out.resolve()}\n")


if __name__ == "__main__":
    main()
