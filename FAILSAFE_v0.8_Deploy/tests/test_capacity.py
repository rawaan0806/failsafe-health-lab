import unittest
from capacity import capacity_run
from server import calculate, parse_config

class CapacityTests(unittest.TestCase):
    def test_repeatable(self):
        self.assertEqual(capacity_run(250,42),capacity_run(250,42))
    def test_more_staff_reduces_waiting(self):
        low=capacity_run(500,42,discharge_staff=1,booking_staff=2)
        high=capacity_run(500,42,discharge_staff=8,booking_staff=8)
        self.assertGreater(low['mean_wait_minutes'],high['mean_wait_minutes'])
    def test_more_arrivals_increases_wait(self):
        low=capacity_run(500,42,arrivals_per_day=30)
        high=capacity_run(500,42,arrivals_per_day=150)
        self.assertLess(low['mean_wait_minutes'],high['mean_wait_minutes'])
    def test_invalid_capacity_rejected(self):
        with self.assertRaises(ValueError):
            parse_config({'capacity':{'discharge_staff':0}})
    def test_response_contains_capacity(self):
        r=calculate({'patients':50,'validation_seeds':1})
        self.assertEqual(r['version'],'0.6')
        self.assertEqual(r['capacity']['patients'],50)
        self.assertIn('replicated_mean_wait_range',r['capacity'])

if __name__=='__main__': unittest.main()
