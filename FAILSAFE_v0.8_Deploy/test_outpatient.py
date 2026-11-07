import unittest
from outpatient import analyze, parse_outpatient

class OutpatientTests(unittest.TestCase):
    def test_default(self):
        r=analyze({})
        self.assertTrue(r['synthetic_only'])
        self.assertEqual(r['baseline']['patients'],100)
        self.assertGreaterEqual(r['optimized']['completed_before_close'],r['baseline']['completed_before_close'])
        self.assertLessEqual(r['recommendation']['estimated_cost_eur'],650)
    def test_reproducible(self):
        self.assertEqual(analyze({}),analyze({}))
    def test_no_reception(self):
        r=analyze({'receptionists':0,'budget':0})
        self.assertEqual(r['baseline']['completed_before_close'],0)
        self.assertEqual(r['baseline']['blocked_stages']['reception'],r['scenario']['patients'] - r['baseline']['blocked_stages']['parking'])
    def test_budget_zero(self):
        r=analyze({'budget':0})
        self.assertEqual(r['recommendation']['estimated_cost_eur'],0)
    def test_invalid_percentage(self):
        with self.assertRaises(ValueError):parse_outpatient({'routine_pct':80,'diagnostic_pct':50})
    def test_reject_unexpected_data(self):
        with self.assertRaises(ValueError):parse_outpatient({'patient_name':'Someone'})
    def test_reject_negative_cost(self):
        with self.assertRaises(ValueError):parse_outpatient({'unit_costs':{'receptionists':-10}})
    def test_staff_improves(self):
        from outpatient import simulate, _patients
        cfg=parse_outpatient({'patients':150,'receptionists':1})
        cohort=_patients(cfg)
        a=simulate(cfg,cohort)
        b=simulate({**cfg,'receptionists':3},cohort)
        self.assertGreaterEqual(b['completed_before_close'],a['completed_before_close'])
