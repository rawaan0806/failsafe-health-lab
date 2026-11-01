"""Verify dashboard replay events are the same events behind the queue metrics."""
import unittest
from capacity import capacity_run
from server import calculate_trace


class VisualTraceTests(unittest.TestCase):
    def test_trace_exact_mean_wait_and_threshold(self):
        result = capacity_run(500, 42, include_trace=True)
        rows = result['trace']
        self.assertEqual(len(rows), 500)
        waits = [(r[1] - r[0]) + (r[3] - r[2]) for r in rows]
        self.assertAlmostEqual(sum(waits) / 500, result['mean_wait_minutes'], delta=.06)
        self.assertEqual(sum(w > 120.0001 for w in waits), result['over_120min'])
        self.assertGreaterEqual(result['end_minute'], max(row[4] for row in rows))

    def test_event_order_for_each_patient(self):
        for count in (50, 500, 1500):
            with self.subTest(count=count):
                rows = capacity_run(count, 17, discharge_staff=1, booking_staff=2, include_trace=True)['trace']
                self.assertTrue(all(row == sorted(row) for row in rows))
                # Station 2 must be served in finish-of-station-1 order (FCFS).
                finished_first = sorted(rows, key=lambda r:r[2])
                starts_second = [r[3] for r in finished_first]
                self.assertEqual(starts_second, sorted(starts_second))

    def test_trace_paired_patient_work_across_staffing(self):
        a = capacity_run(300, 12, discharge_staff=1, booking_staff=2, include_trace=True)['trace']
        b = capacity_run(300, 12, discharge_staff=4, booking_staff=4, include_trace=True)['trace']
        for ra, rb in zip(a,b):
            self.assertEqual(ra[0], rb[0])
            self.assertAlmostEqual(ra[2] - ra[1], rb[2] - rb[1], delta=.002)
            self.assertAlmostEqual(ra[4] - ra[3], rb[4] - rb[3], delta=.002)

    def test_trace_api_validations_and_version(self):
        body = {'config': {'patients': 50}, 'added_discharge_staff': 1, 'added_booking_staff': 2}
        data = calculate_trace(body)
        self.assertEqual(data['version'], '0.6')
        self.assertTrue(data['synthetic_only'])
        self.assertEqual(data['staffing'], {'discharge_staff': 4, 'booking_staff': 4})
        self.assertEqual(len(data['queue']['trace']), 50)
        with self.assertRaises(ValueError):
            calculate_trace({**body, 'added_booking_staff': 5})
        with self.assertRaises(ValueError):
            calculate_trace({**body, 'config': {'patients': 50, 'capacity': {'discharge_staff': 30}}})
        with self.assertRaises(ValueError):
            calculate_trace({**body, 'config': {'patients': 50}, 'unexpected': 'x'})

    def test_trace_repeatable_and_staff_affects_wait(self):
        a=calculate_trace({'config': {'patients': 500}, 'added_discharge_staff': 0, 'added_booking_staff': 0})
        self.assertEqual(a, calculate_trace({'config': {'patients': 500}, 'added_discharge_staff': 0, 'added_booking_staff': 0}))
        b=calculate_trace({'config': {'patients': 500}, 'added_discharge_staff': 2, 'added_booking_staff': 2})
        self.assertGreater(a['queue']['mean_wait_minutes'],b['queue']['mean_wait_minutes'])

if __name__ == '__main__': unittest.main()
