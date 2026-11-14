"""core/report: the dynamic-drive artifact - CLI loading, bridge correlation, and Markdown rendering.

Unit-level, unlike tests/test_report_static.py's subprocess goldens: those need a log fixture this
checkout doesn't have (tests/fixtures/logs/, missing in this environment, pre-existing and
unrelated to this feature - see test_report_golden.py's own "no fixture logs found" failure). These
exercise core.report.cli.load_artifact, core.report.correlate and core.report.markdown_dynamic
directly against in-memory data instead.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import SENTRY_DIR

sys.path.insert(0, str(SENTRY_DIR))

from core.report import assemble, correlate  # noqa: E402
from core.report.cli import load_artifact  # noqa: E402
from core.report.markdown_dynamic import dynamic_section  # noqa: E402
from core.report.markdown_static import bridge_lines  # noqa: E402


class FakeTracker:
    """Just enough of WebViewTracker for correlate.py: no runtime bridges observed at all."""

    def __init__(self) -> None:
        self.webviews: dict = {}
        self.trusted_origins: set = set()


def registration(class_name: str, name: str = "AppBridge") -> dict:
    return {
        "name": name,
        "name_status": "resolved",
        "name_source": {"kind": "const-string", "ref": None},
        "class_name": class_name,
        "class_resolution": "exact",
        "candidate_classes": [class_name],
        "methods": [],
        "call_site": {"class": class_name, "method": "onCreate", "signature": "onCreate(android.os.Bundle)", "dex": "classes.dex", "offset": 0},
        "webview_receiver": "verified",
    }


def static(class_name: str) -> dict:
    return {
        "status": "completed",
        "target_sdk": 33,
        "all_public_methods_exposed": False,
        "registrations": [registration(class_name)],
        "bridge_classes": [],
        "removals": [],
    }


class LoadArtifact(unittest.TestCase):
    def test_loads_a_valid_schema_1_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dynamic-drive.json"
            path.write_text(json.dumps({"schema": 1, "activities_launched": []}), encoding="utf-8")
            self.assertEqual(load_artifact(path, "dynamic-drive"), {"schema": 1, "activities_launched": []})

    def test_none_path_is_none(self) -> None:
        self.assertIsNone(load_artifact(None, "dynamic-drive"))

    def test_missing_or_bad_schema_warns_and_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_schema = Path(tmp) / "a.json"
            bad_schema.write_text(json.dumps({"schema": 2}), encoding="utf-8")
            self.assertIsNone(load_artifact(bad_schema, "dynamic-drive"))
            self.assertIsNone(load_artifact(Path(tmp) / "missing.json", "dynamic-drive"))


class CorrelateAutomation(unittest.TestCase):
    def test_marks_a_successfully_launched_registering_class(self) -> None:
        dynamic = {"activities_launched": [{"class_name": "com.example.app.MainActivity", "ok": True}]}
        (bridge,) = correlate.correlate(static("com.example.app.MainActivity"), FakeTracker(), dynamic)["bridges"]
        self.assertEqual(bridge["provenance"], "static-only")
        self.assertTrue(bridge["automation_attempted"])

    def test_marks_false_when_the_launch_failed_or_targeted_another_class(self) -> None:
        dynamic = {"activities_launched": [{"class_name": "com.example.app.MainActivity", "ok": False}]}
        (bridge,) = correlate.correlate(static("com.example.app.MainActivity"), FakeTracker(), dynamic)["bridges"]
        self.assertFalse(bridge["automation_attempted"])

        dynamic_other = {"activities_launched": [{"class_name": "com.example.app.Other", "ok": True}]}
        (bridge,) = correlate.correlate(static("com.example.app.MainActivity"), FakeTracker(), dynamic_other)["bridges"]
        self.assertFalse(bridge["automation_attempted"])

    def test_none_when_no_dynamic_data_was_given_at_all(self) -> None:
        (bridge,) = correlate.correlate(static("com.example.app.MainActivity"), FakeTracker())["bridges"]
        self.assertIsNone(bridge["automation_attempted"])

    def test_bridge_lines_render_the_automation_line_only_when_known(self) -> None:
        bridge = {
            "interfaceName": "AppBridge",
            "className": "com.example.app.MainActivity",
            "provenance": "static-only",
            "static": {"class_resolution": "exact", "methods": []},
            "registered_in": ["com.example.app.MainActivity.onCreate(android.os.Bundle)"],
            "sensitive_methods": [],
            "automation_attempted": True,
        }
        self.assertTrue(any("Automation attempted" in line for line in bridge_lines(bridge)))
        self.assertFalse(any("Automation attempted" in line for line in bridge_lines({**bridge, "automation_attempted": None})))


class AssembleAndMarkdownDynamicSection(unittest.TestCase):
    def test_build_report_includes_dynamic_drive_only_when_given(self) -> None:
        findings = type("F", (), {"sorted_findings": lambda self: [], "risk_score": lambda self: 0, "severity_counts": lambda self: {}})()
        report = assemble.build_report(FakeTracker(), findings, [], 0)
        self.assertNotIn("dynamic_drive", report)
        report = assemble.build_report(FakeTracker(), findings, [], 0, dynamic_section={"activities_launched": []})
        self.assertEqual(report["dynamic_drive"], {"activities_launched": []})

    def test_renders_launches_and_actions(self) -> None:
        section = {
            "activities_launched": [{"class_name": "com.example.app.MainActivity", "ok": True, "command": "am start -n x"}],
            "ui_actions": [{"kind": "dialog", "label": "id/allow", "center": [25, 25]}, {"kind": "tap", "label": "id/next", "center": [5, 5]}],
        }
        lines = dynamic_section(section)
        text = "\n".join(lines)
        self.assertIn("## Dynamic Coverage", text)
        self.assertIn("Activities launched by automation: 1 (1 succeeded)", text)
        self.assertIn("UI actions performed: 2 (1 system-dialog dismissal(s))", text)
        self.assertIn("`com.example.app.MainActivity` (ok): `am start -n x`", text)
        self.assertIn("Dismissed `id/allow` at (25, 25)", text)
        self.assertIn("Tapped `id/next` at (5, 5)", text)

    def test_renders_something_sensible_when_empty(self) -> None:
        text = "\n".join(dynamic_section({"activities_launched": [], "ui_actions": []}))
        self.assertIn("Activities launched by automation: 0 (0 succeeded)", text)
        self.assertNotIn("### Activities launched", text)
        self.assertNotIn("### UI actions", text)


if __name__ == "__main__":
    unittest.main()
