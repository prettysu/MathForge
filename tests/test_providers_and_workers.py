import unittest

from mathforge.providers import CodexProvider, MockProvider, ProviderResult
from mathforge.workers import TaskSpec, build_task, validate_worker_result


class WorkerContractTests(unittest.TestCase):
    def test_mock_proof_worker_marks_missing_step_as_immature(self):
        task = build_task("proof", "Study convergence.", [])

        result = MockProvider().run(task)

        self.assertIsInstance(result, ProviderResult)
        self.assertEqual(result.claims[0]["id"], "C-001")
        self.assertEqual(result.claims[0]["maturity"], "plausible_sketch")
        self.assertTrue(result.claims[0]["known_gaps"])

    def test_mock_computation_worker_emits_a_narrow_empirical_claim(self):
        task = build_task("computation", "Study convergence.", [])

        result = MockProvider().run(task)

        self.assertEqual(result.claims[0]["kind"], "empirical")
        self.assertNotEqual(result.claims[0]["maturity"], "verified_by_reviewer")
        self.assertEqual(result.claims[0]["evidence"][0]["type"], "computation")

    def test_worker_result_validation_requires_claims_and_response(self):
        task = build_task("proof", "Study convergence.", [])
        errors = validate_worker_result(
            ProviderResult(response_markdown="", claims=[], metadata={}),
            task,
        )

        self.assertIn("missing response markdown", errors)
        self.assertIn("missing claims", errors)


class CodexProviderTests(unittest.TestCase):
    def test_missing_codex_executable_is_a_structured_provider_failure(self):
        task = build_task("proof", "Study convergence.", [])
        result = CodexProvider(executable="definitely-not-a-real-codex").run(task)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "PROVIDER_UNAVAILABLE")
