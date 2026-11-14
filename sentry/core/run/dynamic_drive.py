"""core/run: the one background-thread entry point both runners use to drive dynamic coverage.

Sequenced, not concurrent with each other: launch every profiled activity first (so their WebViews
and bridges register under the attached hooks), then crawl whatever is now on screen by tapping
around. Both steps are already best-effort and silent-by-default on their own; this module just
chains them so core/runners/local.py and core/runners/container/entry.py each start one thread.
"""

from __future__ import annotations

from typing import Any

from core.host import Host
from core.run.intent_launch import launch_profiled_activities
from core.run.ui_automator import explore_ui
from core.run.workspace import Workspace


def drive_coverage(host: Host, adb: Any, workspace: Workspace, package: str, verbose: bool) -> None:
    launch_profiled_activities(host, adb, workspace, package, verbose)
    explore_ui(host, adb, package, verbose)
