"""core/report: render the dynamic-drive automation log (activities launched, UI taps) as Markdown."""

from __future__ import annotations

from typing import Any


def dynamic_section(section: dict[str, Any]) -> list[str]:
    launches = section.get("activities_launched") or []
    actions = section.get("ui_actions") or []
    ok_count = sum(1 for launch in launches if launch.get("ok"))
    dialogs = sum(1 for action in actions if action.get("kind") == "dialog")
    lines = [
        "",
        "## Dynamic Coverage",
        "",
        f"- Activities launched by automation: {len(launches)} ({ok_count} succeeded)",
        f"- UI actions performed: {len(actions)} ({dialogs} system-dialog dismissal(s))",
        "",
    ]
    if launches:
        lines.append("### Activities launched")
        lines.append("")
        for launch in launches:
            status = "ok" if launch.get("ok") else f"failed after {launch.get('attempts')} attempt(s)"
            lines.append(f"- `{launch['class_name']}` ({status}): `{launch['command']}`")
        lines.append("")
    if actions:
        lines.append("### UI actions")
        lines.append("")
        for action in actions:
            verb = "Dismissed" if action.get("kind") == "dialog" else "Tapped"
            x, y = action.get("center", [None, None])
            lines.append(f"- {verb} `{action.get('label')}` at ({x}, {y})")
        lines.append("")
    return lines
