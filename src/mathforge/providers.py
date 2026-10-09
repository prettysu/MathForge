from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from .workers import TaskSpec


@dataclass(slots=True)
class ProviderResult:
    response_markdown: str
    claims: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    error_code: str | None = None
    error_message: str | None = None


class Provider:
    def run(self, task: TaskSpec) -> ProviderResult:
        raise NotImplementedError


def _claim(
    claim_id: str,
    statement: str,
    kind: str,
    maturity: str,
    evidence_type: str,
    worker_role: str,
    task_id: str,
    *,
    known_gaps: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": claim_id,
        "statement": statement,
        "kind": kind,
        "maturity": maturity,
        "status": "PROPOSED",
        "assumptions": ["The demo objective uses a bounded deterministic example."],
        "evidence": [{"path": f"workers/{worker_role}/response.md", "type": evidence_type}],
        "dependencies": [],
        "known_gaps": known_gaps or [],
        "source": {"worker_role": worker_role, "task_id": task_id},
    }


class MockProvider(Provider):
    """Deterministic provider that demonstrates both a gate failure and success."""

    def run(self, task: TaskSpec) -> ProviderResult:
        if task.role == "proof":
            claim = _claim(
                "C-001",
                "The demo iteration converges for every admissible initialization.",
                "theorem",
                "plausible_sketch",
                "proof",
                task.role,
                task.task_id,
                known_gaps=["The uniform bound over initializations is not proved."],
            )
            return ProviderResult(
                response_markdown=(
                    "# Proof Exploration\n\n"
                    "The reduction is plausible, but the uniform bound remains open.\n"
                ),
                claims=[claim],
                metadata={"maturity_summary": "incomplete proof route"},
            )
        if task.role == "computation":
            claim = _claim(
                "C-002",
                "For the configured finite demo grid, the direct and spectral computations agree.",
                "empirical",
                "plausible_sketch",
                "computation",
                task.role,
                task.task_id,
            )
            return ProviderResult(
                response_markdown=(
                    "# Computation Check\n\n"
                    "The direct and independent spectral implementations agree on the demo grid.\n"
                ),
                claims=[claim],
                metadata={
                    "tests": {
                        "status": "PASS",
                        "test_count": 2,
                        "max_error": 0.0,
                    },
                    "computation_gate": "PASS",
                },
            )
        if task.role == "literature":
            claim = _claim(
                "C-003",
                "The demo uses no external literature claim.",
                "scope",
                "plausible_sketch",
                "literature",
                task.role,
                task.task_id,
            )
            return ProviderResult(
                response_markdown="# Literature Review\n\nNo external theorem is required for this demo.\n",
                claims=[claim],
                metadata={"sources": []},
            )
        if task.role == "reviewer":
            return ProviderResult(
                response_markdown="# Review\n\nThe proof claim is immature; the empirical claim is narrow and supported.\n",
                claims=[],
                metadata={
                    "reviewer_id": "mock-reviewer-001",
                    "decision": "REQUEST_CHANGES",
                    "approved_claims": ["C-002", "C-003"],
                    "blocked_claims": ["C-001"],
                    "required_changes": ["Supply the missing uniform bound."],
                    "checks": {
                        "assumptions": "PASS",
                        "proof_completeness": "FAIL",
                        "source_fidelity": "PASS",
                        "computation": "PASS",
                        "overclaiming": "FAIL",
                    },
                },
            )
        return ProviderResult(
            response_markdown="# Synthesis\n\nOnly approved claims may be synthesized.\n",
            claims=[],
            metadata={},
        )


class CodexProvider(Provider):
    def __init__(self, executable: str = "codex", timeout_seconds: int = 300):
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def run(self, task: TaskSpec) -> ProviderResult:
        if shutil.which(self.executable) is None:
            return ProviderResult(
                response_markdown="",
                claims=[],
                ok=False,
                error_code="PROVIDER_UNAVAILABLE",
                error_message=f"executable not found: {self.executable}",
            )
        prompt = (
            "You are the {role} worker in MathForge. Return a JSON object with "
            "response_markdown, claims, and metadata. Do not claim proof maturity "
            "verified_by_reviewer; only the reviewer may do that.\n\n"
            "Objective: {objective}\n"
            "Input files: {inputs}\n"
        ).format(role=task.role, objective=task.objective, inputs=", ".join(task.input_files))
        try:
            completed = subprocess.run(
                [self.executable, "exec", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ProviderResult(
                response_markdown="",
                claims=[],
                ok=False,
                error_code="PROVIDER_EXECUTION_FAILED",
                error_message=str(exc),
            )
        if completed.returncode != 0:
            return ProviderResult(
                response_markdown=completed.stdout,
                claims=[],
                ok=False,
                error_code="PROVIDER_EXIT_NONZERO",
                error_message=completed.stderr.strip() or "codex exec failed",
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return ProviderResult(
                response_markdown=completed.stdout,
                claims=[],
                ok=False,
                error_code="INVALID_PROVIDER_JSON",
                error_message="Codex output was not valid JSON",
            )
        return ProviderResult(
            response_markdown=str(payload.get("response_markdown", "")),
            claims=list(payload.get("claims", [])),
            metadata=dict(payload.get("metadata", {})),
        )
