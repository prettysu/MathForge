import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args, cwd=ROOT):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "mathforge", *args],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


class CliTests(unittest.TestCase):
    def test_help_is_available(self):
        result = run_cli("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("claim-gated", result.stdout)

    def test_mock_run_reports_blocked_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_cli("run", "Study convergence.", "--root", directory, "--provider", "mock")

            self.assertEqual(result.returncode, 0)
            self.assertIn("BLOCKED", result.stdout)
            self.assertIn("Run:", result.stdout)

    def test_promote_rejects_a_blocked_run(self):
        with tempfile.TemporaryDirectory() as directory:
            run_result = run_cli("run", "Study convergence.", "--root", directory, "--provider", "mock")
            run_id = next(line.split(":", 1)[1].strip() for line in run_result.stdout.splitlines() if line.startswith("Run:"))

            result = run_cli("promote", run_id, "--root", directory)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Gate failed", result.stderr)
