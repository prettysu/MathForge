from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import GateError, MathForgeError
from .gates import check_promotion, promote
from .pipeline import run_cycle
from .storage import load_run
from .synthesis import synthesize_final_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mathforge",
        description="claim-gated, auditable multi-agent workflows for mathematical reasoning.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize a MathForge directory")
    init.add_argument("directory", type=Path)

    run = subparsers.add_parser("run", help="run a complete research cycle")
    run.add_argument("objective")
    run.add_argument("--root", type=Path, default=Path("."))
    run.add_argument("--provider", choices=["mock", "codex"], default="mock")

    for name, help_text in (
        ("status", "show a run manifest"),
        ("promote", "apply the promotion gate"),
        ("synthesize", "write the final report from approved claims"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("run_id")
        command.add_argument("--root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            args.directory.mkdir(parents=True, exist_ok=True)
            (args.directory / "runs").mkdir(exist_ok=True)
            print(f"Initialized MathForge directory: {args.directory.resolve()}")
            return 0
        if args.command == "run":
            run = run_cycle(args.root, args.objective, args.provider)
            print(f"Run: {run.manifest.run_id}")
            print(f"Status: {run.manifest.status.value}")
            print(f"Report: {run.path / 'final' / 'report.md'}")
            return 0
        run = load_run(args.root, args.run_id)
        if args.command == "status":
            print(json.dumps(run.manifest.to_dict(), indent=2))
            return 0
        if args.command == "promote":
            registry = promote(run)
            print(f"Promoted {len(registry['claims'])} claims.")
            return 0
        if args.command == "synthesize":
            report = synthesize_final_report(run)
            print(f"Report: {report}")
            return 0
    except GateError as exc:
        print(f"Gate failed: {exc}", file=sys.stderr)
        return 2
    except (MathForgeError, ValueError, OSError) as exc:
        print(f"MathForge error: {exc}", file=sys.stderr)
        return 1
    return 1
