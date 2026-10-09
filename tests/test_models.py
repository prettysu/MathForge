import unittest

from mathforge.errors import ValidationError
from mathforge.models import (
    Claim,
    ClaimMaturity,
    ClaimStatus,
    ReviewDecision,
    ReviewOutcome,
    RunManifest,
    RunStatus,
    validate_claim,
)


class ClaimModelTests(unittest.TestCase):
    def test_claim_round_trips_with_typed_values(self):
        claim = Claim.from_dict(
            {
                "id": "C-001",
                "statement": "A useful statement.",
                "kind": "theorem",
                "maturity": "plausible_sketch",
                "status": "PROPOSED",
                "assumptions": ["A1"],
                "evidence": [{"path": "proof.md", "type": "proof"}],
                "dependencies": [],
                "known_gaps": ["A missing limit argument."],
                "source": {"worker_role": "proof", "task_id": "task-1"},
            }
        )

        self.assertEqual(claim.maturity, ClaimMaturity.PLAUSIBLE_SKETCH)
        self.assertEqual(claim.status, ClaimStatus.PROPOSED)
        self.assertEqual(claim.to_dict()["id"], "C-001")
        self.assertEqual(claim.to_dict()["maturity"], "plausible_sketch")

    def test_claim_requires_id_statement_assumptions_and_evidence(self):
        claim = Claim.from_dict(
            {
                "id": "",
                "statement": "",
                "kind": "theorem",
                "maturity": "incomplete",
                "status": "PROPOSED",
                "assumptions": [],
                "evidence": [],
                "dependencies": [],
                "known_gaps": [],
                "source": {"worker_role": "proof", "task_id": "task-1"},
            }
        )

        errors = validate_claim(claim)

        self.assertIn("missing claim id", errors)
        self.assertIn("missing statement", errors)
        self.assertIn("missing assumptions", errors)
        self.assertIn("missing evidence", errors)

    def test_invalid_claim_enum_is_rejected(self):
        with self.assertRaises(ValidationError):
            Claim.from_dict(
                {
                    "id": "C-001",
                    "statement": "Statement",
                    "kind": "theorem",
                    "maturity": "invented",
                    "status": "PROPOSED",
                    "assumptions": ["A1"],
                    "evidence": [{"path": "proof.md", "type": "proof"}],
                    "dependencies": [],
                    "known_gaps": [],
                    "source": {"worker_role": "proof", "task_id": "task-1"},
                }
            )


class ReviewModelTests(unittest.TestCase):
    def test_review_decision_round_trips(self):
        decision = ReviewDecision.from_dict(
            {
                "reviewer_id": "reviewer-001",
                "decision": "REQUEST_CHANGES",
                "approved_claims": [],
                "blocked_claims": ["C-001"],
                "required_changes": ["Close the proof gap."],
                "checks": {"proof_completeness": "FAIL"},
            }
        )

        self.assertEqual(decision.outcome, ReviewOutcome.REQUEST_CHANGES)
        self.assertEqual(decision.to_dict()["blocked_claims"], ["C-001"])


class RunManifestTests(unittest.TestCase):
    def test_manifest_round_trips(self):
        manifest = RunManifest.from_dict(
            {
                "run_id": "run-001",
                "objective": "Study convergence.",
                "provider": "mock",
                "status": "CREATED",
                "created_at": "2026-10-09T12:00:00Z",
                "required_roles": ["proof", "reviewer", "synthesis"],
            }
        )

        self.assertEqual(manifest.status, RunStatus.CREATED)
        self.assertEqual(manifest.to_dict()["required_roles"], ["proof", "reviewer", "synthesis"])
