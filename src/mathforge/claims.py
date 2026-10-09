from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import GateError, ValidationError
from .models import (
    Claim,
    ClaimMaturity,
    ClaimStatus,
    ReviewDecision,
    ReviewOutcome,
    validate_claim,
)
from .storage import RunContext


WORKER_ROLES = ("proof", "literature", "computation")


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


def _requires_computation(claim_kind: str) -> bool:
    return claim_kind.lower() in {
        "theorem",
        "formula",
        "asymptotic",
        "deterministic_equivalent",
    }


def _computation_passed(run: RunContext) -> bool:
    path = run.path / "workers" / "computation" / "tests.json"
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "PASS"
    except json.JSONDecodeError:
        return False


def _eligible_for_registry(run: RunContext, claim: Claim) -> bool:
    if claim.status is not ClaimStatus.APPROVED:
        return False
    if _is_proof_like(claim.kind) and claim.maturity is not ClaimMaturity.VERIFIED_BY_REVIEWER:
        return False
    if any(not (run.path / evidence.path).exists() for evidence in claim.evidence):
        return False
    if _requires_computation(claim.kind) and not _computation_passed(run):
        return False
    return True


def _claim_files(run: RunContext) -> list[Path]:
    return [run.path / "workers" / role / "claims.json" for role in WORKER_ROLES]


def _write_claim_file(path: Path, claims: list[Claim]) -> None:
    path.write_text(
        json.dumps([claim.to_dict() for claim in claims], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_claims(run: RunContext) -> list[Claim]:
    claims: list[Claim] = []
    seen: set[str] = set()
    for path in _claim_files(run):
        if not path.exists():
            continue
        try:
            raw_items = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"invalid claims JSON: {path}") from exc
        if not isinstance(raw_items, list):
            raise ValidationError(f"claims file must contain a list: {path}")
        for raw in raw_items:
            claim = Claim.from_dict(raw)
            errors = validate_claim(claim)
            if errors:
                raise ValidationError(f"{claim.id}: {'; '.join(errors)}")
            if claim.id in seen:
                raise ValidationError(f"duplicate claim id: {claim.id}")
            seen.add(claim.id)
            claims.append(claim)
    return claims


def _persist_claim_statuses(run: RunContext, updated: dict[str, Claim]) -> None:
    for path in _claim_files(run):
        if not path.exists():
            continue
        raw_items = json.loads(path.read_text(encoding="utf-8"))
        claims = [Claim.from_dict(raw) for raw in raw_items]
        for claim in claims:
            if claim.id in updated:
                claim.status = updated[claim.id].status
        _write_claim_file(path, claims)


def apply_review(run: RunContext, raw_decision: dict[str, Any]) -> ReviewDecision:
    decision = ReviewDecision.from_dict(raw_decision)
    claims = load_claims(run)
    by_id = {claim.id: claim for claim in claims}
    referenced = set(decision.approved_claims) | set(decision.blocked_claims)
    unknown = sorted(referenced - set(by_id))
    if unknown:
        raise GateError("UNKNOWN_CLAIM", f"review references unknown claims: {unknown}")
    if set(decision.approved_claims) & set(decision.blocked_claims):
        raise GateError("CONFLICTING_REVIEW", "a claim cannot be both approved and blocked")
    updated: dict[str, Claim] = {}
    for claim_id in decision.approved_claims:
        by_id[claim_id].status = ClaimStatus.APPROVED
        updated[claim_id] = by_id[claim_id]
    for claim_id in decision.blocked_claims:
        by_id[claim_id].status = ClaimStatus.BLOCKED
        updated[claim_id] = by_id[claim_id]
    remaining = set(by_id) - referenced
    for claim_id in remaining:
        by_id[claim_id].status = (
            ClaimStatus.REQUEST_CHANGES
            if decision.outcome is ReviewOutcome.REQUEST_CHANGES
            else ClaimStatus.REVIEWING
        )
        updated[claim_id] = by_id[claim_id]
    _persist_claim_statuses(run, updated)
    review_dir = run.path / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir / "decision.json").write_text(
        json.dumps(decision.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return decision


def build_claim_registry(run: RunContext) -> dict[str, Any]:
    claims = load_claims(run)
    reviewer_path = run.path / "review" / "decision.json"
    reviewer_ids: list[str] = []
    if reviewer_path.exists():
        decision = ReviewDecision.from_dict(
            json.loads(reviewer_path.read_text(encoding="utf-8"))
        )
        reviewer_ids.append(decision.reviewer_id)
    approved = []
    for claim in claims:
        if not _eligible_for_registry(run, claim):
            continue
        item = claim.to_dict()
        item["global_id"] = f"{run.manifest.run_id}:{claim.id}"
        item["reviewers"] = reviewer_ids
        approved.append(item)
    registry = {
        "run_id": run.manifest.run_id,
        "claims": approved,
    }
    path = run.path / "claims" / "registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return registry
