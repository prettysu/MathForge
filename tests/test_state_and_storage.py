import json
import tempfile
import unittest
from pathlib import Path

from mathforge.errors import MathForgeError
from mathforge.models import RunStatus
from mathforge.state import transition_run
from mathforge.storage import (
    append_event,
    create_run,
    load_run,
    safe_output_path,
)


class RunStorageTests(unittest.TestCase):
    def test_create_run_persists_manifest_and_loads_it(self):
        with tempfile.TemporaryDirectory() as directory:
            context = create_run(Path(directory), "Study convergence.", "mock")
            loaded = load_run(Path(directory), context.manifest.run_id)

            self.assertEqual(loaded.manifest.objective, "Study convergence.")
            self.assertEqual(loaded.manifest.status, RunStatus.CREATED)
            self.assertTrue((loaded.path / "manifest.json").exists())

    def test_events_are_append_only_json_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            context = create_run(Path(directory), "Study convergence.", "mock")

            append_event(context, "run_created", {"source": "test"})
            append_event(context, "worker_started", {"role": "proof"})

            events = [
                json.loads(line)
                for line in (context.path / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["type"] for event in events], ["run_created", "worker_started"])
            self.assertEqual(events[1]["details"]["role"], "proof")

    def test_output_path_must_stay_inside_run_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            context = create_run(Path(directory), "Study convergence.", "mock")

            valid = safe_output_path(context, "workers/proof/response.md")
            self.assertEqual(valid, context.path / "workers" / "proof" / "response.md")

            with self.assertRaises(MathForgeError):
                safe_output_path(context, "../../outside.txt")


class RunStateTests(unittest.TestCase):
    def test_legal_transitions_are_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            context = create_run(Path(directory), "Study convergence.", "mock")

            transition_run(context, RunStatus.RUNNING)
            transition_run(context, RunStatus.REVIEWING)

            self.assertEqual(load_run(Path(directory), context.manifest.run_id).manifest.status, RunStatus.REVIEWING)

    def test_complete_cannot_be_reached_without_promotion_state(self):
        with tempfile.TemporaryDirectory() as directory:
            context = create_run(Path(directory), "Study convergence.", "mock")

            with self.assertRaises(MathForgeError):
                transition_run(context, RunStatus.COMPLETE)
