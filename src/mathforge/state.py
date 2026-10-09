from __future__ import annotations

from .errors import MathForgeError
from .models import RunStatus
from .storage import RunContext, append_event, save_manifest


_ALLOWED_TRANSITIONS = {
    RunStatus.CREATED: {RunStatus.RUNNING, RunStatus.BLOCKED},
    RunStatus.RUNNING: {RunStatus.REVIEWING, RunStatus.BLOCKED},
    RunStatus.REVIEWING: {RunStatus.RUNNING, RunStatus.BLOCKED},
    RunStatus.BLOCKED: {RunStatus.RUNNING},
    RunStatus.COMPLETE: set(),
}


def transition_run(
    context: RunContext,
    target: RunStatus,
    *,
    promotion_token: bool = False,
) -> None:
    current = context.manifest.status
    if target is RunStatus.COMPLETE and not promotion_token:
        raise MathForgeError("only the promotion gate may complete a run")
    if target not in _ALLOWED_TRANSITIONS[current] and not (
        target is RunStatus.COMPLETE and promotion_token and current is RunStatus.REVIEWING
    ):
        raise MathForgeError(f"illegal run transition: {current} -> {target}")
    context.manifest.status = target
    save_manifest(context)
    append_event(context, "run_status_changed", {"from": current.value, "to": target.value})
