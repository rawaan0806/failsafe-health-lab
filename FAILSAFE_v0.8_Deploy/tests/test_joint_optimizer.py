"""Tests for the capacity-aware combined optimizer and API constraints."""
import unittest

from server import calculate, parse_config


class CombinedOptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.default = calculate({'patients': 120, 'seed': 45, 'budget': 350, 'validation_seeds': 3})

    def test_evaluates_72_combinations(self):
        j = self.default['joint_optimizer']
        self.assertEqual(j['options_evaluated'], 72)
        self.assertEqual(len(j['plans']), 72)
        self.assertEqual(len(set(p['id'] for p in j['plans'])), 72)
        self.assertEqual(j['feasible_options'], sum(x['within_budget'] for x in j['plans']))

    def test_best_feasible_according_to_documented_ranking(self):
        j = self.default['joint_optimizer']
        feasible = [p for p in j['plans'] if p['within_budget']]
        self.assertEqual(j['recommended']['id'], sorted(feasible, key=lambda p: (-p['score'], p['total_cost'], p['id']))[0]['id'])
        self.assertLessEqual(j['recommended']['total_cost'], j['budget_credits'])

    def test_zero_budget_requires_base_staff_and_no_support(self):
        j = calculate({'patients': 80, 'budget': 0, 'validation_seeds': 1})['joint_optimizer']
        self.assertEqual(j['recommended']['id'], 'baseline__d0_b0')
        self.assertEqual(j['recommended']['total_cost'], 0)
        self.assertEqual(j['feasible_options'], 1)

    def test_priorities_change_objective_and_sometimes_recommendations(self):
        w0 = calculate({'patients': 500, 'budget': 350, 'validation_seeds': 3, 'completion_weight': 0})['joint_optimizer']
        w100 = calculate({'patients': 500, 'budget': 350, 'validation_seeds': 3, 'completion_weight': 100})['joint_optimizer']
        self.assertEqual(w0['completion_weight_pct'], 0)
        self.assertEqual(w100['completion_weight_pct'], 100)
        self.assertNotEqual(w0['recommended']['id'], w100['recommended']['id'])
        self.assertAlmostEqual(w0['recommended']['score'], w0['recommended']['mean_timely_queue_pct'], delta=.1)
        self.assertAlmostEqual(w100['recommended']['score'], w100['recommended']['mean_pathway_completion_pct'], delta=.1)

    def test_staffing_affects_queues_not_independent_pathway_pct(self):
        j = self.default['joint_optimizer']
        related = [p for p in j['plans'] if p['plan_id'] == 'baseline']
        self.assertEqual(len(set(p['mean_pathway_completion_pct'] for p in related)), 1)
        self.assertGreaterEqual(related[0]['mean_timely_queue_pct'], 0)
        self.assertLessEqual(related[0]['mean_timely_queue_pct'], 100)

    def test_budget_and_cost_decomposition(self):
        j = self.default['joint_optimizer']
        for p in j['plans']:
            self.assertAlmostEqual(p['total_cost'], p['staff_cost'] + p['intervention_cost'])
        # Staff increments cannot exceed 30 total.
        capped = calculate({'patients': 75, 'validation_seeds': 1,
                            'capacity': {'discharge_staff': 30, 'booking_staff': 30}})
        self.assertEqual(capped['joint_optimizer']['options_evaluated'], 8)

    def test_repeatable_and_api_includes_joint_output(self):
        sample = {'patients': 80, 'seed': 17, 'validation_seeds': 1}
        a = calculate(sample)
        b = calculate(sample)
        self.assertEqual(a['joint_optimizer'], b['joint_optimizer'])
        self.assertEqual(a['version'], '0.6')
        self.assertIn('recommended', a['joint_optimizer'])

    def test_rejects_invalid_weight(self):
        for w in [-1, 101, 10.5, True, '60']:
            with self.subTest(weight=w):
                with self.assertRaises(ValueError):
                    parse_config({'completion_weight': w})


if __name__ == '__main__':
    unittest.main()
