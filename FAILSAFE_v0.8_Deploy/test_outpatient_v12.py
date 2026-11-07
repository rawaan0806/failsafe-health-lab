import unittest
from outpatient import _patients, analyze, parse_outpatient, simulate

class OutpatientCountAndParkingTests(unittest.TestCase):
    def test_exact_counts(self):
        cfg=parse_outpatient(dict(patients=100,routine_count=12,diagnostic_count=21,nurse_count=30,car_count=70))
        rows=_patients(cfg)
        self.assertEqual(sum(x[2]=='routine' for x in rows),12)
        self.assertEqual(sum(x[2]=='diagnostic' for x in rows),21)
        self.assertEqual(sum(x[2]=='specialist' for x in rows),67)
        self.assertEqual(sum(x[3] for x in rows),30)
        self.assertEqual(sum(x[4] for x in rows),70)

    def test_counts_validated(self):
        with self.assertRaises(ValueError):parse_outpatient(dict(patients=100,routine_count=60,diagnostic_count=60))
        with self.assertRaises(ValueError):parse_outpatient(dict(patients=100,nurse_count=110))
        with self.assertRaises(ValueError):parse_outpatient(dict(patients=100,car_count=101))

    def test_parking_available_after_reservations(self):
        cfg=parse_outpatient(dict(parking_spaces=80,parking_reserved=20))
        self.assertEqual(simulate(cfg)['parking_spaces_available'],60)

    def test_reserved_cannot_exceed_total(self):
        with self.assertRaises(ValueError):parse_outpatient(dict(parking_spaces=40,parking_reserved=41))

    def test_all_reserved_blocks_car_visits(self):
        cfg=parse_outpatient(dict(parking_spaces=12,parking_reserved=12,car_count=100))
        r=simulate(cfg)
        self.assertEqual(r['completed_before_close'],0)
        self.assertEqual(r['blocked_stages']['parking'],100)

    def test_optimizer_can_add_parking_if_budget_allows(self):
        r=analyze(dict(parking_spaces=10,parking_reserved=10,car_count=100,budget=200))
        self.assertTrue(r['synthetic_only'])
        self.assertIn('parking_spaces_available',r['baseline'])
        self.assertGreaterEqual(r['optimized']['completed_before_close'],r['baseline']['completed_before_close'])

if __name__ == '__main__':unittest.main()
