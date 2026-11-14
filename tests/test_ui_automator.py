"""core/run/ui_automator: parsing a uiautomator dump and crawling clickable nodes with it."""

from __future__ import annotations

import sys
import unittest

from tests.helpers import SENTRY_DIR

sys.path.insert(0, str(SENTRY_DIR))

from core.host import Result  # noqa: E402
from core.run.ui_automator import DEFAULT_MAX_ACTIONS, INITIAL_DELAY_SECONDS, TAP_SETTLE_SECONDS, explore_ui, parse_clickable_nodes  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
