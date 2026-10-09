from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Claim, validate_claim


@dataclass(slots=True)
class TaskSpec:
    task_id: str
    role: str
    objective: str
    input_files: list[str] = field(default_factory=list)
    output_dir: str = ""


def build_task(role: str, objective: str, input_files: list[str]) -> TaskSpec:
    normalized = role.strip().lower()
    if normalized not in {"proof", "literature", "computation", "reviewer", "synthesis"}:
        raise ValueError(f"unsupported worker role: {role}")
    return TaskSpec(
        task_id=f"task-{normalized}",
        role=normalized,
        objective=objective,
        input_files=list(input_files),
        output_dir=f"workers/{normalized}",
    )


def validate_worker_result(result: Any, task: TaskSpec) -> list[str]:
    errors: list[str] = []
    if not getattr(result, "response_markdown", "").strip():
        errors.append("missing response markdown")
    claims = getattr(result, "claims", None)
    if not isinstance(claims, list) or not claims:
        errors.append("missing claims")
        return errors
    for index, raw_claim in enumerate(claims):
        try:
            claim = Claim.from_dict(raw_claim)
        except Exception as exc:
            errors.append(f"claim {index} invalid: {exc}")
            continue
        errors.extend(f"claim {claim.id}: {error}" for error in validate_claim(claim))
    return errors
