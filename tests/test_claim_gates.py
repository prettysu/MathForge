import json
import tempfile
import unittest
from pathlib import Path

from mathforge.claims import apply_review, build_claim_registry, load_claims
from mathforge.gates import check_promotion, promote
from mathforge.models import RunStatus
from mathforge.providers import MockProvider
from mathforge.storage import create_run
from mathforge.workers import build_task


def write_claims(run, role, claims, metadata=None):
    directory = run.path / "workers" / role
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "response.md").write_text(f"# {role}\nEvidence.\n", encoding="utf-8")
    (directory / "claims.json").write_text(json.dumps(claims, indent=2), encoding="utf-8")
    if metadata is not None:
        (directory / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def claim_from_mock(role):
    return MockProvider().run(build_task(role, "Study convergence.", [])).claims


class ClaimLoadingTests(unittest.TestCase):
    def test_load_claims_reads_claims_from_worker_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            run = create_run(Path(directory), "Study convergence.", "mock")
            write_claims(run, "proof", claim_from_mock("proof"))
            write_claims(run, "computation", claim_from_mock("computation"))

            claims = load_claims(run)

            self.assertEqual({claim.id for claim in claims}, {"C-001", "C-002"})


class PromotionGateTests(unittest.TestCase):
    def test_plausible_sketch_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            run = create_run(Path(directory), "Study convergence.", "mock")
            write_claims(run, "proof", claim_from_mock("proof"))
            write_claims(run, "computation", claim_from_mock("computation"))
            apply_review(
                run,
                {
                    "reviewer_id": "reviewer-001",
                    "decision": "APPROVE",
                    "approved_claims": ["C-001", "C-002"],
                    "blocked_claims": [],
                    "required_changes": [],
                    "checks": {"proof_completeness": "PASS"},
                },
            )

            report = check_promotion(run)

            self.assertFalse(report.passed)
            self.assertTrue(any(error.code == "IMMATURE_CLAIM" for error in report.errors))

    def test_reviewer_approval_is_limited_to_explicit_claim_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            run = create_run(Path(directory), "Study convergence.", "mock")
            write_claims(run, "computation", claim_from_mock("computation"))
            write_claims(run, "proof", claim_from_mock("proof"))
            apply_review(
                run,
                {
                    "reviewer_id": "reviewer-001",
                    "decision": "APPROVE",
                    "approved_claims": ["C-002"],
                    "blocked_claims": [],
                    "required_changes": [],
                    "checks": {},
                },
            )

            registry = build_claim_registry(run)

            self.assertEqual([claim["id"] for claim in registry["claims"]], ["C-002"])

    def test_blocked_claim_prevents_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            run = create_run(Path(directory), "Study convergence.", "mock")
            write_claims(run, "computation", claim_from_mock("computation"))
            apply_review(
                run,
                {
                    "reviewer_id": "reviewer-001",
                    "decision": "BLOCK",
                    "approved_claims": [],
                    "blocked_claims": ["C-002"],
                    "required_changes": ["Reproduce the computation."],
                    "checks": {},
                },
            )

            report = check_promotion(run)

            self.assertFalse(report.passed)
            self.assertTrue(any(error.code == "BLOCKED_CLAIM" for error in report.errors))

    def test_theorem_claim_requires_passing_computation_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            run = create_run(Path(directory), "Study convergence.", "mock")
            theorem = claim_from_mock("proof")[0]
            theorem["maturity"] = "verified_by_reviewer"
            theorem["known_gaps"] = []
            write_claims(run, "proof", [theorem])
            apply_review(
                run,
                {
                    "reviewer_id": "reviewer-001",
                    "decision": "APPROVE",
                    "approved_claims": ["C-001"],
                    "blocked_claims": [],
                    "required_changes": [],
                    "checks": {},
                },
            )

            report = check_promotion(run)

            self.assertFalse(report.passed)
            self.assertTrue(any(error.code == "COMPUTATION_GATE" for error in report.errors))

    def test_ineligible_theorem_is_excluded_from_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            run = create_run(Path(directory), "Study convergence.", "mock")
            theorem = claim_from_mock("proof")[0]
            theorem["maturity"] = "verified_by_reviewer"
            theorem["known_gaps"] = []
            write_claims(run, "proof", [theorem])
            apply_review(
                run,
                {
                    "reviewer_id": "reviewer-001",
                    "decision": "APPROVE",
                    "approved_claims": ["C-001"],
                    "blocked_claims": [],
                    "required_changes": [],
                    "checks": {},
                },
            )

            registry = build_claim_registry(run)

            self.assertEqual(registry["claims"], [])

    def test_approved_run_can_promote_and_change_status(self):
        with tempfile.TemporaryDirectory() as directory:
            run = create_run(Path(directory), "Study convergence.", "mock")
            empirical = claim_from_mock("computation")
            write_claims(run, "computation", empirical)
            (run.path / "workers" / "computation" / "tests.json").write_text(
                json.dumps({"status": "PASS"}), encoding="utf-8"
            )
            apply_review(
                run,
                {
                    "reviewer_id": "reviewer-001",
                    "decision": "APPROVE",
                    "approved_claims": ["C-002"],
                    "blocked_claims": [],
                    "required_changes": [],
                    "checks": {},
                },
            )
            run.manifest.status = RunStatus.REVIEWING

            registry = promote(run)

            self.assertEqual(run.manifest.status, RunStatus.COMPLETE)
            self.assertEqual(registry["claims"][0]["global_id"], f"{run.manifest.run_id}:C-002")
