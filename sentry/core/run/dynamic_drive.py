"""core/run: the one background-thread entry point both runners use to drive dynamic coverage.

Sequenced, not concurrent with each other: launch every profiled activity first (so their WebViews
and bridges register under the attached hooks), then crawl whatever is now on screen by tapping
around. Both steps are already best-effort and silent-by-default on their own; this module chains
them and writes what happened to target/dynamic-drive.json, so core/report can later show whether
a static-only bridge was at least attempted by automation even though it was never observed at
runtime. Writing the artifact is itself best-effort: a run stopped before this thread finishes just
means the artifact (and that report section) is missing, same as any other skipped step here.
"""

from __future__ import annotations

import json
import time
from typing import Any

from core.host import Host
from core.run.intent_launch import launch_profiled_activities
from core.run.ui_automator import explore_ui
from core.run.workspace import Workspace

SCHEMA = 1


def drive_coverage(host: Host, adb: Any, workspace: Workspace, package: str, verbose: bool) -> None:
    started = time.monotonic()
    activities_launched = launch_profiled_activities(host, adb, workspace, package, verbose)
    ui_actions = explore_ui(host, adb, package, verbose)
    artifact = {
        "schema": SCHEMA,
        "package": package,
        "activities_launched": activities_launched,
        "ui_actions": ui_actions,
        "seconds": round(time.monotonic() - started, 2),
    }
    try:
        workspace.dynamic_drive.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass
