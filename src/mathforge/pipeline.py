from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .claims import apply_review, build_claim_registry
from .gates import check_promotion, promote
from .models import RunStatus
from .planner import plan_objective
from .providers import CodexProvider, MockProvider, Provider, ProviderResult
from .state import transition_run
from .storage import RunContext, append_event, create_run
from .synthesis import synthesize_final_report
from .workers import TaskSpec, build_task, validate_worker_result


def _provider(name: str) -> Provider:
    if name == "mock":
        return MockProvider()
    if name == "codex":
        return CodexProvider()
    raise ValueError(f"unsupported provider: {name}")


def _write_task(run: RunContext, task: TaskSpec) -> None:
    path = run.path / "tasks" / f"{task.role}.json"
    path.write_text(
        json.dumps(
            {
                "task_id": task.task_id,
                "role": task.role,
                "objective": task.objective,
                "input_files": task.input_files,
                "output_dir": task.output_dir,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_worker_result(run: RunContext, task: TaskSpec, result: ProviderResult) -> None:
    directory = run.path / task.output_dir
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "response.md").write_text(result.response_markdown, encoding="utf-8")
    (directory / "claims.json").write_text(
        json.dumps(result.claims, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (directory / "metadata.json").write_text(
        json.dumps(result.metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tests = result.metadata.get("tests")
    if isinstance(tests, dict):
        (directory / "tests.json").write_text(
            json.dumps(tests, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _fail_run(run: RunContext, code: str, message: str) -> RunContext:
    append_event(run, "run_failed", {"code": code, "message": message})
    if run.manifest.status is not RunStatus.BLOCKED:
        transition_run(run, RunStatus.BLOCKED)
    failure = run.path / "failed_explorations" / f"{code.lower()}.md"
    failure.write_text(f"# {code}\n\n{message}\n", encoding="utf-8")
    return run


def _run_worker(run: RunContext, provider: Provider, task: TaskSpec) -> ProviderResult | None:
    _write_task(run, task)
    append_event(run, "worker_started", {"role": task.role, "task_id": task.task_id})
    result = provider.run(task)
    if not result.ok:
        _fail_run(run, result.error_code or "WORKER_FAILED", result.error_message or "worker failed")
        return None
    errors = validate_worker_result(result, task) if task.role != "reviewer" else []
    if errors:
        _fail_run(run, "INVALID_WORKER_OUTPUT", "; ".join(errors))
        return None
    _write_worker_result(run, task, result)
    append_event(run, "worker_finished", {"role": task.role, "task_id": task.task_id})
    return result


def run_cycle(root: Path, objective: str, provider_name: str = "mock") -> RunContext:
    run = create_run(root, objective, provider_name)
    transition_run(run, RunStatus.RUNNING)
    plan = plan_objective(objective)
    (run.path / "plan.json").write_text(
        json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    provider = _provider(provider_name)
    literature_result = _run_worker(
        run,
        provider,
        build_task("literature", objective, ["plan.json"]),
    )
    if literature_result is None:
        synthesize_final_report(run)
        return run
    proof_result = _run_worker(run, provider, build_task("proof", objective, ["plan.json"]))
    if proof_result is None:
        synthesize_final_report(run)
        return run
    computation_result = _run_worker(
        run,
        provider,
        build_task("computation", objective, ["plan.json", "workers/proof/response.md"]),
    )
    if computation_result is None:
        synthesize_final_report(run)
        return run
    transition_run(run, RunStatus.REVIEWING)
    reviewer_task = build_task(
        "reviewer",
        objective,
        [
            "plan.json",
            "workers/literature/claims.json",
            "workers/proof/claims.json",
            "workers/computation/claims.json",
        ],
    )
    reviewer_result = _run_worker(run, provider, reviewer_task)
    if reviewer_result is None:
        synthesize_final_report(run)
        return run
    apply_review(run, reviewer_result.metadata)
    build_claim_registry(run)
    report = check_promotion(run)
    if report.passed:
        promote(run)
    else:
        transition_run(run, RunStatus.BLOCKED)
        append_event(
            run,
            "promotion_blocked",
            {
                "errors": [
                    {"code": error.code, "message": error.message, "claim_id": error.claim_id}
                    for error in report.errors
                ]
            },
        )
    synthesize_final_report(run)
    return run
