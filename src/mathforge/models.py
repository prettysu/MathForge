from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .errors import ValidationError


class ClaimMaturity(StrEnum):
    VERIFIED_BY_REVIEWER = "verified_by_reviewer"
    PLAUSIBLE_SKETCH = "plausible_sketch"
    INCOMPLETE = "incomplete"
    LIKELY_FALSE = "likely_false"
    COUNTEREXAMPLE_FOUND = "counterexample_found"


class ClaimStatus(StrEnum):
    PROPOSED = "PROPOSED"
    REVIEWING = "REVIEWING"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    BLOCKED = "BLOCKED"
    APPROVED = "APPROVED"


class ReviewOutcome(StrEnum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    BLOCK = "BLOCK"


class RunStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    REVIEWING = "REVIEWING"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValidationError(f"{key} must be a string")
    return value


def _list_of_strings(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError(f"{key} must be a list of strings")
    return list(value)


@dataclass(slots=True)
class Evidence:
    path: str
    type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        if not isinstance(data, dict):
            raise ValidationError("evidence item must be an object")
        path = _required_string(data, "path")
        evidence_type = _required_string(data, "type")
        if not path or not evidence_type:
            raise ValidationError("evidence path and type must be non-empty")
        return cls(path=path, type=evidence_type)

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "type": self.type}


@dataclass(slots=True)
class ClaimSource:
    worker_role: str
    task_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaimSource":
        if not isinstance(data, dict):
            raise ValidationError("source must be an object")
        return cls(
            worker_role=_required_string(data, "worker_role"),
            task_id=_required_string(data, "task_id"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"worker_role": self.worker_role, "task_id": self.task_id}


@dataclass(slots=True)
class Claim:
    id: str
    statement: str
    kind: str
    maturity: ClaimMaturity
    status: ClaimStatus
    assumptions: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    known_gaps: list[str] = field(default_factory=list)
    source: ClaimSource = field(default_factory=lambda: ClaimSource("", ""))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Claim":
        try:
            maturity = ClaimMaturity(_required_string(data, "maturity"))
            status = ClaimStatus(_required_string(data, "status"))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        evidence_data = data.get("evidence", [])
        if not isinstance(evidence_data, list):
            raise ValidationError("evidence must be a list")
        return cls(
            id=_required_string(data, "id"),
            statement=_required_string(data, "statement"),
            kind=_required_string(data, "kind"),
            maturity=maturity,
            status=status,
            assumptions=_list_of_strings(data, "assumptions"),
            evidence=[Evidence.from_dict(item) for item in evidence_data],
            dependencies=_list_of_strings(data, "dependencies"),
            known_gaps=_list_of_strings(data, "known_gaps"),
            source=ClaimSource.from_dict(data.get("source", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "kind": self.kind,
            "maturity": self.maturity.value,
            "status": self.status.value,
            "assumptions": list(self.assumptions),
            "evidence": [item.to_dict() for item in self.evidence],
            "dependencies": list(self.dependencies),
            "known_gaps": list(self.known_gaps),
            "source": self.source.to_dict(),
        }


@dataclass(slots=True)
class ReviewDecision:
    reviewer_id: str
    outcome: ReviewOutcome
    approved_claims: list[str] = field(default_factory=list)
    blocked_claims: list[str] = field(default_factory=list)
    required_changes: list[str] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewDecision":
        try:
            outcome = ReviewOutcome(_required_string(data, "decision"))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        checks = data.get("checks", {})
        if not isinstance(checks, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in checks.items()
        ):
            raise ValidationError("checks must be an object of string values")
        return cls(
            reviewer_id=_required_string(data, "reviewer_id"),
            outcome=outcome,
            approved_claims=_list_of_strings(data, "approved_claims"),
            blocked_claims=_list_of_strings(data, "blocked_claims"),
            required_changes=_list_of_strings(data, "required_changes"),
            checks=dict(checks),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer_id": self.reviewer_id,
            "decision": self.outcome.value,
            "approved_claims": list(self.approved_claims),
            "blocked_claims": list(self.blocked_claims),
            "required_changes": list(self.required_changes),
            "checks": dict(self.checks),
        }


@dataclass(slots=True)
class RunManifest:
    run_id: str
    objective: str
    provider: str
    status: RunStatus
    created_at: str
    required_roles: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunManifest":
        try:
            status = RunStatus(_required_string(data, "status"))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return cls(
            run_id=_required_string(data, "run_id"),
            objective=_required_string(data, "objective"),
            provider=_required_string(data, "provider"),
            status=status,
            created_at=_required_string(data, "created_at"),
            required_roles=_list_of_strings(data, "required_roles"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "objective": self.objective,
            "provider": self.provider,
            "status": self.status.value,
            "created_at": self.created_at,
            "required_roles": list(self.required_roles),
        }


def validate_claim(claim: Claim) -> list[str]:
    errors: list[str] = []
    if not claim.id.strip():
        errors.append("missing claim id")
    if not claim.statement.strip():
        errors.append("missing statement")
    if not claim.assumptions:
        errors.append("missing assumptions")
    if not claim.evidence:
        errors.append("missing evidence")
    if not claim.source.worker_role.strip() or not claim.source.task_id.strip():
        errors.append("missing source metadata")
    return errors
