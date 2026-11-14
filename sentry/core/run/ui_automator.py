"""core/run: a tiny UI Automator crawler - dump the screen, tap something useful, repeat.

No intent-data profile needed: it just clicks around whatever's on screen (app chrome, dialogs,
WebView content with native-looking controls) so more code runs under the attached hooks. A system
dialog (a permission prompt, in practice) is dismissed on sight regardless of package, since it
otherwise blocks every tap aimed at the app underneath it; among the app's own nodes, one that
looks like forward progress (`next`, `allow`, ...) beats one that looks like a dead end (`back`,
`cancel`, ...). A device without `uiautomator`, an unparsable dump, or nothing left to click just
ends the crawl early.
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
DISMISS_HINTS = ("allow", "while using the app", "only this time", "i agree", "accept", "got it", "ok", "continue")
POSITIVE_HINTS = ("next", "continue", "login", "log in", "sign in", "accept", "agree", "start", "submit", "confirm", "done")
NEGATIVE_HINTS = ("back", "cancel", "skip", "close", "deny", "not now", "no thanks", "exit")


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
        label = resource_id or text or class_name or "(unlabeled)"
        center = ((x1 + x2) // 2, (y1 + y2) // 2)
        nodes.append({"key": (resource_id, text, attrib["bounds"]), "center": center, "label": label})
    return nodes


def find_dismiss_node(xml_text: str) -> dict[str, Any] | None:
    """A system-dialog button to tap away regardless of package, or None if there's nothing to dismiss."""
    for node in parse_clickable_nodes(xml_text, package=None):
        if any(hint in node["label"].lower() for hint in DISMISS_HINTS):
            return node
    return None


def priority(node: dict[str, Any]) -> int:
    label = node["label"].lower()
    positive, negative = any(h in label for h in POSITIVE_HINTS), any(h in label for h in NEGATIVE_HINTS)
    return 1 if positive else -1 if negative else 0


def pick_target(nodes: list[dict[str, Any]], visited: set[tuple[str, str, str]]) -> dict[str, Any] | None:
    pool = [node for node in nodes if node["key"] not in visited] or nodes
    return max(pool, key=priority) if pool else None


def explore_ui(host: Host, adb: Any, package: str | None, verbose: bool, max_actions: int = DEFAULT_MAX_ACTIONS) -> list[dict[str, Any]]:
    host.sleep(INITIAL_DELAY_SECONDS)
    visited: set[tuple[str, str, str]] = set()
    log: list[dict[str, Any]] = []
    for _ in range(max_actions):
        if adb.run(["shell", "uiautomator", "dump", DUMP_PATH], quiet=True).returncode != 0:
            break
        dump = adb.run(["shell", "cat", DUMP_PATH], stdout=CAPTURE, stderr=DISCARD)
        dismiss = find_dismiss_node(dump.stdout)
        target, kind = (dismiss, "dialog") if dismiss else (pick_target(parse_clickable_nodes(dump.stdout, package), visited), "tap")
        if target is None:
            break
        visited.add(target["key"])
        x, y = target["center"]
        adb.run(["shell", "input", "tap", str(x), str(y)])
        log.append({"kind": kind, "label": target["label"], "center": [x, y]})
        if verbose:
            verb = "dismiss" if kind == "dialog" else "tap"
            host.echo(f"ui {verb} -> {target['label']} at ({x}, {y})")
        host.sleep(TAP_SETTLE_SECONDS)
    return log
