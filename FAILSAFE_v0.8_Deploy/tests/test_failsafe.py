"""Run with `python -m unittest discover -s tests -v` from the starter folder."""
import tempfile
from pathlib import Path
import unittest

from failsafe import STAGES, generate_patients, simulate, summarize, run


class FailsafeTests(unittest.TestCase):
    def test_reproducible(self):
        cohort = generate_patients(100, 42)
        self.assertEqual(cohort, generate_patients(100, 42))
        self.assertEqual(simulate(cohort, 42, "baseline"), simulate(cohort, 42, "baseline"))

    def test_intervention_cannot_make_paired_completion_worse(self):
        cohort = generate_patients(500, 42)
        baseline = simulate(cohort, 42, "baseline")
        for name in ("teachback", "medication_support", "followup_support", "all"):
            candidate = simulate(cohort, 42, name)
            for old, new in zip(baseline, candidate):
                if old.fully_completed:
                    self.assertTrue(new.fully_completed, (name, old.patient.patient_id))

    def test_counts_and_blocking(self):
        cohort = generate_patients(250, 1)
        results = simulate(cohort, 1, "baseline")
        summary = summarize(results)
        self.assertEqual(summary["patients"], 250)
        self.assertEqual(summary["fully_completed"] + summary["patients_with_one_or_more_failures"], 250)
        for row in results:
            self.assertFalse(row.handoff == "fail" and row.medication != "blocked")
            self.assertFalse(row.booking == "fail" and row.attendance != "blocked")
            self.assertEqual(row.fully_completed, all(row.status(stage) == "pass" for stage in STAGES))

    def test_export(self):
        with tempfile.TemporaryDirectory() as directory:
            results = run(20, 5, directory)
            self.assertEqual(results["scenarios"]["baseline"]["patients"], 20)
            self.assertTrue((Path(directory) / "summary.json").exists())
            self.assertTrue((Path(directory) / "all.csv").exists())


if __name__ == "__main__":
    unittest.main()
