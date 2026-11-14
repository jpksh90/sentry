"""core/run/dynamic_drive: sequences the activity launcher and the UI crawler behind one thread target."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import SENTRY_DIR

sys.path.insert(0, str(SENTRY_DIR))

from core.host import Result  # noqa: E402
from core.run.dynamic_drive import drive_coverage  # noqa: E402
from core.run.ui_automator import INITIAL_DELAY_SECONDS  # noqa: E402
from core.run.workspace import Workspace  # noqa: E402
from tests.fakes import FakeHost  # noqa: E402


class DriveCoverage(unittest.TestCase):
    def test_runs_the_launcher_then_the_crawler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Workspace(Path(tmp))
            ws.target.mkdir(parents=True)
            profile = {
                "status": "completed",
                "activities": [
                    {"class_name": "com.example.app.MainActivity", "exported": True, "exported_declared": True,
                     "intent_filters": [], "intent_keys": []}
                ],
            }
            ws.intent_profile.write_text(json.dumps(profile), encoding="utf-8")
            host = FakeHost(respond=lambda cmd: Result(0, ""))
            drive_coverage(host, host, ws, "com.example.app", False)
        runs = [c[1] for c in host.calls if c[0] == "run"]
        self.assertTrue(runs[0][1].startswith("am start"), runs[0])  # the launcher goes first
        self.assertEqual([r[1] for r in runs[1:]], ["uiautomator", "cat"])  # then the crawler
        # the launcher's own delay, then the crawler's initial delay before its first dump
        self.assertIn(("sleep", INITIAL_DELAY_SECONDS), [c for c in host.calls if c[0] == "sleep"])

    def test_runs_the_crawler_even_with_no_profile_to_launch_from(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Workspace(Path(tmp))
            ws.target.mkdir(parents=True)
            host = FakeHost(respond=lambda cmd: Result(0, ""))
            drive_coverage(host, host, ws, "com.example.app", False)
        self.assertEqual([c[1][1] for c in host.calls if c[0] == "run"], ["uiautomator", "cat"])  # no am start, straight to crawling


if __name__ == "__main__":
    unittest.main()
