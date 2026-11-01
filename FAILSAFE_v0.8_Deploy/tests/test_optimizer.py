"""Tests for resource optimization over explicitly synthetic assumptions."""
import tempfile
import json
import unittest
from pathlib import Path

from failsafe import generate_patients, simulate, summarize
from optimizer import plans, credits_for, evaluate, export_result


class OptimizerTests(unittest.TestCase):
    def test_eight_distinct_plans_and_costs(self):
        names = [name for name, _, _ in plans()]
        self.assertEqual(len(names), 8)
        self.assertEqual(len(set(names)), 8)
        self.assertEqual(credits_for((), 500), 0)
        self.assertEqual(credits_for(tuple(['medication_navigation', 'followup_coordination']), 500), 350.0)

    def test_zero_budget_baseline(self):
        result, _ = evaluate(80, seed=42, budget=0, validation_seeds=2)
        self.assertEqual(result['recommended_plan_id'], 'baseline')
        self.assertEqual(result['feasible_plans'], 1)

    def test_high_budget_all_allowed_and_optimal(self):
        result, _ = evaluate(150, seed=13, budget=10_000, validation_seeds=3)
        self.assertEqual(result['feasible_plans'], 8)
        self.assertEqual(result['recommended_plan_id'], 'teachback_and_interpreter+medication_navigation+followup_coordination')
        self.assertEqual(result['recommended_plan']['cost_credits'], 157.5)

    def test_budget_bound_and_best_achievable_score(self):
        for budget in (0, 100, 150, 175, 325, 350, 525):
            result, _ = evaluate(500, seed=42, budget=budget, validation_seeds=2)
            feasible = [x for x in result['possible_plans'] if x['cost_credits'] <= budget]
            self.assertTrue(feasible)
            self.assertLessEqual(result['recommended_plan']['cost_credits'], budget)
            best = sorted(feasible, key=lambda r: (-r['validation']['mean_completed'],r['cost_credits'],r['id']))[0]
            self.assertEqual(result['recommended_plan_id'], best['id'])

    def test_reproducible_and_export(self):
        a, runs = evaluate(50, seed=77, budget=100, validation_seeds=2)
        b, _ = evaluate(50, seed=77, budget=100, validation_seeds=2)
        self.assertEqual(a, b)
        self.assertEqual(len(runs), 8)
        with tempfile.TemporaryDirectory() as folder:
            export_result(Path(folder), a, runs)
            saved = json.loads((Path(folder) / 'optimization.json').read_text())
            self.assertEqual(saved['recommended_plan_id'], a['recommended_plan_id'])
            self.assertTrue((Path(folder) / 'baseline.csv').exists())

    def test_compatible_with_original_baseline_and_all_scenarios(self):
        res, runs = evaluate(250, seed=15, budget=300, validation_seeds=2)
        cohort = generate_patients(250, 15)
        self.assertEqual(summarize(runs['baseline']), summarize(simulate(cohort, 15, 'baseline')))
        full_id = 'teachback_and_interpreter+medication_navigation+followup_coordination'
        self.assertEqual(summarize(runs[full_id]), summarize(simulate(cohort, 15, 'all')))


if __name__ == '__main__':
    unittest.main()
