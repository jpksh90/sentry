"""core/run/ui_automator: parsing a uiautomator dump and crawling clickable nodes with it."""

from __future__ import annotations

import sys
import unittest

from tests.helpers import SENTRY_DIR

sys.path.insert(0, str(SENTRY_DIR))

from core.host import Result  # noqa: E402
from core.run.ui_automator import (  # noqa: E402
    DEFAULT_MAX_ACTIONS, INITIAL_DELAY_SECONDS, TAP_SETTLE_SECONDS, explore_ui, find_dismiss_node, parse_clickable_nodes,
    pick_target, priority,
)
from tests.fakes import FakeHost  # noqa: E402

DUMP = """<?xml version="1.0"?>
<hierarchy>
 <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.example.app"
       clickable="false" enabled="true" bounds="[0,0][1080,1920]">
  <node index="0" text="Login" resource-id="com.example.app:id/login" class="android.widget.Button"
        package="com.example.app" clickable="true" enabled="true" bounds="[100,200][300,260]"/>
  <node index="1" text="" resource-id="com.example.app:id/disabled" class="android.widget.Button"
        package="com.example.app" clickable="true" enabled="false" bounds="[100,300][300,360]"/>
  <node index="2" text="SystemThing" resource-id="" class="android.widget.ImageView"
        package="com.android.systemui" clickable="true" enabled="true" bounds="[0,0][50,50]"/>
  <node index="3" text="" resource-id="com.example.app:id/zero" class="android.view.View"
        package="com.example.app" clickable="true" enabled="true" bounds="[10,10][10,10]"/>
 </node>
</hierarchy>
"""

TWO_NODE_DUMP = """<?xml version="1.0"?>
<hierarchy>
 <node text="A" resource-id="id/a" class="android.widget.Button" package="com.example.app"
       clickable="true" enabled="true" bounds="[0,0][10,10]"/>
 <node text="B" resource-id="id/b" class="android.widget.Button" package="com.example.app"
       clickable="true" enabled="true" bounds="[20,20][30,30]"/>
</hierarchy>
"""

PERMISSION_DIALOG_DUMP = """<?xml version="1.0"?>
<hierarchy>
 <node text="Deny" resource-id="id/deny" class="android.widget.Button" package="com.google.android.permissioncontroller"
       clickable="true" enabled="true" bounds="[0,0][10,10]"/>
 <node text="Allow" resource-id="id/allow" class="android.widget.Button" package="com.google.android.permissioncontroller"
       clickable="true" enabled="true" bounds="[20,20][30,30]"/>
 <node text="Underneath" resource-id="id/underneath" class="android.widget.Button" package="com.example.app"
       clickable="true" enabled="true" bounds="[40,40][50,50]"/>
</hierarchy>
"""

PRIORITY_DUMP = """<?xml version="1.0"?>
<hierarchy>
 <node text="Cancel" resource-id="id/cancel" class="android.widget.Button" package="com.example.app"
       clickable="true" enabled="true" bounds="[0,0][10,10]"/>
 <node text="Next" resource-id="id/next" class="android.widget.Button" package="com.example.app"
       clickable="true" enabled="true" bounds="[20,20][30,30]"/>
</hierarchy>
"""


class ParseClickableNodes(unittest.TestCase):
    def test_filters_disabled_wrong_package_and_zero_area(self) -> None:
        (node,) = parse_clickable_nodes(DUMP, "com.example.app")
        self.assertEqual(node["label"], "com.example.app:id/login")
        self.assertEqual(node["center"], (200, 230))
        self.assertEqual(node["key"], ("com.example.app:id/login", "Login", "[100,200][300,260]"))

    def test_no_package_filter_still_excludes_disabled_and_zero_area(self) -> None:
        nodes = parse_clickable_nodes(DUMP, None)
        self.assertEqual({n["label"] for n in nodes}, {"com.example.app:id/login", "SystemThing"})

    def test_malformed_xml_is_empty(self) -> None:
        self.assertEqual(parse_clickable_nodes("not xml", None), [])
        self.assertEqual(parse_clickable_nodes("", None), [])


class FindDismissNode(unittest.TestCase):
    def test_matches_regardless_of_package(self) -> None:
        node = find_dismiss_node(PERMISSION_DIALOG_DUMP)
        self.assertEqual(node["label"], "id/allow")

    def test_none_when_nothing_matches(self) -> None:
        self.assertIsNone(find_dismiss_node(TWO_NODE_DUMP))
        self.assertIsNone(find_dismiss_node(""))


class Priority(unittest.TestCase):
    def test_positive_beats_neutral_beats_negative(self) -> None:
        self.assertGreater(priority({"label": "Next"}), priority({"label": "Whatever"}))
        self.assertGreater(priority({"label": "Whatever"}), priority({"label": "Cancel"}))

    def test_pick_target_prefers_priority_within_the_unvisited_pool(self) -> None:
        cancel = {"key": ("c",), "label": "Cancel"}
        next_ = {"key": ("n",), "label": "Next"}
        self.assertEqual(pick_target([cancel, next_], visited=set()), next_)

    def test_pick_target_falls_back_to_the_full_pool_once_all_are_visited(self) -> None:
        cancel = {"key": ("c",), "label": "Cancel"}
        self.assertEqual(pick_target([cancel], visited={("c",)}), cancel)

    def test_pick_target_is_none_when_there_is_nothing(self) -> None:
        self.assertIsNone(pick_target([], visited=set()))


class ExploreUi(unittest.TestCase):
    def test_sleeps_before_the_first_dump(self) -> None:
        host = FakeHost(respond=lambda cmd: Result(0, ""))
        explore_ui(host, host, "com.example.app", False)
        self.assertEqual(host.calls[0], ("sleep", INITIAL_DELAY_SECONDS))

    def test_stops_immediately_when_dump_fails(self) -> None:
        host = FakeHost(respond=lambda cmd: Result(1))
        explore_ui(host, host, "com.example.app", False)
        runs = [c[1] for c in host.calls if c[0] == "run"]
        self.assertEqual(runs, [["shell", "uiautomator", "dump", "/sdcard/sentry-ui-dump.xml"]])

    def test_stops_when_nothing_clickable(self) -> None:
        host = FakeHost(respond=lambda cmd: Result(0, ""))
        explore_ui(host, host, "com.example.app", False)
        runs = [c[1][1] for c in host.calls if c[0] == "run"]
        self.assertEqual(runs, ["uiautomator", "cat"])  # one dump, one (empty) cat, then it gives up

    def test_taps_unvisited_nodes_before_repeating(self) -> None:
        def respond(cmd):
            return Result(0, TWO_NODE_DUMP if cmd[1] == "cat" else "")

        host = FakeHost(respond=respond)
        explore_ui(host, host, "com.example.app", False, max_actions=3)
        taps = [c[1][-2:] for c in host.calls if c[0] == "run" and c[1][2] == "tap"]
        self.assertEqual(taps, [["5", "5"], ["25", "25"], ["5", "5"]])  # A, then B, then back to A
        self.assertEqual([c for c in host.calls if c[0] == "sleep"], [("sleep", INITIAL_DELAY_SECONDS)] + [("sleep", TAP_SETTLE_SECONDS)] * 3)

    def test_verbose_echoes_each_tap(self) -> None:
        def respond(cmd):
            return Result(0, TWO_NODE_DUMP if cmd[1] == "cat" else "")

        host = FakeHost(respond=respond)
        buf = []
        host.echo = lambda *lines, err=False: buf.extend(lines)  # type: ignore[method-assign]
        explore_ui(host, host, "com.example.app", True, max_actions=1)
        self.assertEqual(buf, ["ui tap -> id/a at (5, 5)"])

    def test_default_max_actions_is_twenty(self) -> None:
        self.assertEqual(DEFAULT_MAX_ACTIONS, 20)

    def test_returns_a_log_of_what_it_did(self) -> None:
        def respond(cmd):
            return Result(0, TWO_NODE_DUMP if cmd[1] == "cat" else "")

        host = FakeHost(respond=respond)
        log = explore_ui(host, host, "com.example.app", False, max_actions=1)
        self.assertEqual(log, [{"kind": "tap", "label": "id/a", "center": [5, 5]}])

    def test_dismisses_a_system_dialog_before_touching_the_app_underneath(self) -> None:
        dumps = iter([PERMISSION_DIALOG_DUMP, TWO_NODE_DUMP])

        def respond(cmd):
            return Result(0, next(dumps) if cmd[1] == "cat" else "")

        host = FakeHost(respond=respond)
        log = explore_ui(host, host, "com.example.app", False, max_actions=2)
        self.assertEqual(
            log,
            [{"kind": "dialog", "label": "id/allow", "center": [25, 25]}, {"kind": "tap", "label": "id/a", "center": [5, 5]}],
        )

    def test_dialog_dismissal_ignores_the_package_filter(self) -> None:
        host = FakeHost(respond=lambda cmd: Result(0, PERMISSION_DIALOG_DUMP if cmd[1] == "cat" else ""))
        log = explore_ui(host, host, "com.example.app", False, max_actions=1)
        self.assertEqual(log[0]["kind"], "dialog")  # the dialog belongs to a different package entirely

    def test_prefers_forward_progress_over_document_order(self) -> None:
        host = FakeHost(respond=lambda cmd: Result(0, PRIORITY_DUMP if cmd[1] == "cat" else ""))
        log = explore_ui(host, host, "com.example.app", False, max_actions=1)
        self.assertEqual(log, [{"kind": "tap", "label": "id/next", "center": [25, 25]}])  # Cancel comes first in the dump


if __name__ == "__main__":
    unittest.main()
