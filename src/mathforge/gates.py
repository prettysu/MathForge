from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .claims import build_claim_registry, load_claims
from .errors import GateError, ValidationError
from .models import ClaimMaturity, ClaimStatus, ReviewDecision, ReviewOutcome, RunStatus
from .state import transition_run
from .storage import RunContext, append_event


@dataclass(slots=True)
class GateReport:
    passed: bool
    errors: list[GateError] = field(default_factory=list)


def _review(run: RunContext) -> ReviewDecision | None:
    path = run.path / "review" / "decision.json"
    if not path.exists():
        return None
    return ReviewDecision.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _computation_passed(run: RunContext) -> bool:
    path = run.path / "workers" / "computation" / "tests.json"
    if not path.exists():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return value.get("status") == "PASS"


def _requires_computation(claim_kind: str) -> bool:
    return claim_kind.lower() in {
        "theorem",
        "formula",
        "asymptotic",
        "deterministic_equivalent",
    }


def _is_proof_like(claim_kind: str) -> bool:
    return claim_kind.lower() in {
        "theorem",
        "lemma",
        "proposition",
        "proof",
        "formula",
        "asymptotic",
        "deterministic_equivalent",
    }


def check_promotion(run: RunContext) -> GateReport:
    errors: list[GateError] = []
    try:
        claims = load_claims(run)
    except ValidationError as exc:
        return GateReport(False, [GateError("INVALID_CLAIMS", str(exc))])
    decision = _review(run)
    if decision is None:
        errors.append(GateError("MISSING_REVIEW", "no reviewer decision exists"))
    elif decision.outcome is not ReviewOutcome.APPROVE:
        errors.append(
            GateError(
                "REVIEW_NOT_APPROVED",
                f"review decision is {decision.outcome.value}",
            )
        )
    if not claims:
        errors.append(GateError("NO_CLAIMS", "no substantive claims were produced"))
    for claim in claims:
        if claim.status is ClaimStatus.BLOCKED or (
            decision and claim.id in decision.blocked_claims
        ):
            errors.append(GateError("BLOCKED_CLAIM", "claim is blocked", claim.id))
        if claim.status is not ClaimStatus.APPROVED:
            errors.append(GateError("CLAIM_NOT_APPROVED", "claim is not approved", claim.id))
        if (
            claim.status is ClaimStatus.APPROVED
            and _is_proof_like(claim.kind)
            and claim.maturity is not ClaimMaturity.VERIFIED_BY_REVIEWER
        ):
            errors.append(
                GateError(
                    "IMMATURE_CLAIM",
                    f"maturity is {claim.maturity.value}, not verified_by_reviewer",
                    claim.id,
                )
            )
        for evidence in claim.evidence:
            if not (run.path / evidence.path).exists():
                errors.append(
                    GateError("MISSING_EVIDENCE", f"evidence file does not exist: {evidence.path}", claim.id)
                )
        if _requires_computation(claim.kind) and not _computation_passed(run):
            errors.append(
                GateError(
                    "COMPUTATION_GATE",
                    "claim requires passing computation evidence",
                    claim.id,
                )
            )
    if decision:
        approved = set(decision.approved_claims)
        actual = {claim.id for claim in claims}
        unknown_approved = sorted(approved - actual)
        if unknown_approved:
            errors.append(
                GateError("UNKNOWN_CLAIM", f"review approves unknown claims: {unknown_approved}")
            )
    return GateReport(not errors, errors)


def promote(run: RunContext) -> dict[str, Any]:
    report = check_promotion(run)
    if not report.passed:
        append_event(
            run,
            "promotion_blocked",
            {"errors": [{"code": error.code, "message": error.message, "claim_id": error.claim_id} for error in report.errors]},
        )
        raise report.errors[0]
    registry = build_claim_registry(run)
    if run.manifest.status is not RunStatus.REVIEWING:
        raise GateError("INVALID_RUN_STATUS", "run must be REVIEWING before promotion")
    transition_run(run, RunStatus.COMPLETE, promotion_token=True)
    append_event(run, "run_promoted", {"approved_claims": len(registry["claims"])})
    return registry
