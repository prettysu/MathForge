from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .errors import MathForgeError, ValidationError
from .models import RunManifest, RunStatus


@dataclass(slots=True)
class RunContext:
    root: Path
    path: Path
    manifest: RunManifest


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON file: {path}") from exc


def create_run(root: Path, objective: str, provider: str) -> RunContext:
    if not objective.strip():
        raise ValidationError("objective must be non-empty")
    root = root.resolve()
    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    path = root / "runs" / run_id
    for relative in (
        "tasks",
        "workers/proof",
        "workers/literature",
        "workers/computation",
        "review",
        "claims",
        "failed_explorations",
        "final",
    ):
        (path / relative).mkdir(parents=True, exist_ok=True)
    manifest = RunManifest(
        run_id=run_id,
        objective=objective,
        provider=provider,
        status=RunStatus.CREATED,
        created_at=_now(),
        required_roles=["literature", "proof", "computation", "reviewer", "synthesis"],
    )
    _write_json(path / "manifest.json", manifest.to_dict())
    (path / "events.jsonl").touch()
    return RunContext(root=root, path=path, manifest=manifest)


def load_run(root: Path, run_id: str) -> RunContext:
    root = root.resolve()
    path = root / "runs" / run_id
    manifest = RunManifest.from_dict(_read_json(path / "manifest.json"))
    if manifest.run_id != run_id:
        raise ValidationError("manifest run_id does not match requested run")
    return RunContext(root=root, path=path, manifest=manifest)


def save_manifest(context: RunContext) -> None:
    _write_json(context.path / "manifest.json", context.manifest.to_dict())


def append_event(context: RunContext, event_type: str, details: dict) -> None:
    if not event_type.strip():
        raise ValidationError("event type must be non-empty")
    event = {
        "timestamp": _now(),
        "type": event_type,
        "details": details,
    }
    with (context.path / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def safe_output_path(context: RunContext, relative: str) -> Path:
    candidate = (context.path / relative).resolve()
    try:
        candidate.relative_to(context.path.resolve())
    except ValueError as exc:
        raise MathForgeError(f"output path escapes run directory: {relative}") from exc
    return candidate
