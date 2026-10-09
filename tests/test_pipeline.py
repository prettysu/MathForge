import tempfile
import unittest
from pathlib import Path

from mathforge.models import RunStatus
from mathforge.pipeline import run_cycle
from mathforge.synthesis import synthesize_final_report


class PipelineTests(unittest.TestCase):
    def test_mock_cycle_blocks_immature_proof_but_preserves_approved_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            run = run_cycle(Path(directory), "Study convergence.", "mock")

            self.assertEqual(run.manifest.status, RunStatus.BLOCKED)
            registry = (run.path / "claims" / "registry.json").read_text(encoding="utf-8")
            report_path = synthesize_final_report(run)
            report = report_path.read_text(encoding="utf-8")

            self.assertIn("C-002", registry)
            self.assertNotIn("C-001", registry)
            self.assertIn("direct and spectral computations agree", report)
            self.assertNotIn("The demo iteration converges for every admissible initialization", report)

    def test_mock_cycle_writes_auditable_worker_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            run = run_cycle(Path(directory), "Study convergence.", "mock")

            self.assertTrue((run.path / "plan.json").exists())
            self.assertTrue((run.path / "workers" / "literature" / "response.md").exists())
            self.assertTrue((run.path / "workers" / "proof" / "response.md").exists())
            self.assertTrue((run.path / "workers" / "computation" / "tests.json").exists())
            self.assertTrue((run.path / "review" / "decision.json").exists())
            self.assertTrue((run.path / "events.jsonl").read_text(encoding="utf-8"))
