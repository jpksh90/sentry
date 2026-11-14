"""core/run: a tiny UI Automator crawler - dump the screen, tap an unvisited clickable node, repeat.

Generic dynamic-coverage driving to go with core/run/intent_launch.py's targeted activity launches:
this doesn't read the intent-data profile at all, it just clicks around whatever is on screen (the
app's own chrome, dialogs, WebView content with native-looking controls) so more code runs under
the attached hooks. Best-effort only, like the rest of core/run/dynamic_drive.py's pipeline: a device
without `uiautomator`, an unparsable dump, or nothing left to click just ends the crawl early.
"""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

from core.host import CAPTURE, DISCARD, Host

DUMP_PATH = "/sdcard/sentry-ui-dump.xml"
INITIAL_DELAY_SECONDS = 2.0
TAP_SETTLE_SECONDS = 1.0
DEFAULT_MAX_ACTIONS = 20
BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


def parse_clickable_nodes(xml_text: str, package: str | None) -> list[dict[str, Any]]:
    """Clickable, enabled nodes with positive-area bounds, optionally restricted to one app package."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []
    nodes = []
    for node in root.iter("node"):
        attrib = node.attrib
        if attrib.get("clickable") != "true" or attrib.get("enabled") != "true":
            continue
        if package and attrib.get("package") != package:
            continue
        match = BOUNDS_RE.match(attrib.get("bounds", ""))
        if not match:
            continue
        x1, y1, x2, y2 = (int(value) for value in match.groups())
        if x2 <= x1 or y2 <= y1:
            continue
        resource_id, text, class_name = attrib.get("resource-id", ""), attrib.get("text", ""), attrib.get("class", "")
        nodes.append(
            {
                "key": (resource_id, text, attrib["bounds"]),
                "center": ((x1 + x2) // 2, (y1 + y2) // 2),
                "label": resource_id or text or class_name or "(unlabeled)",
            }
        )
    return nodes


def explore_ui(host: Host, adb: Any, package: str | None, verbose: bool, max_actions: int = DEFAULT_MAX_ACTIONS) -> None:
    host.sleep(INITIAL_DELAY_SECONDS)
    visited: set[tuple[str, str, str]] = set()
    for _ in range(max_actions):
        if adb.run(["shell", "uiautomator", "dump", DUMP_PATH], quiet=True).returncode != 0:
            break
        dump = adb.run(["shell", "cat", DUMP_PATH], stdout=CAPTURE, stderr=DISCARD)
        nodes = parse_clickable_nodes(dump.stdout, package)
        candidates = [node for node in nodes if node["key"] not in visited] or nodes
        if not candidates:
            break
        target = candidates[0]
        visited.add(target["key"])
        x, y = target["center"]
        adb.run(["shell", "input", "tap", str(x), str(y)])
        if verbose:
            host.echo(f"ui tap -> {target['label']} at ({x}, {y})")
        host.sleep(TAP_SETTLE_SECONDS)
