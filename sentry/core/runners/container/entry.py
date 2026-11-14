"""core/runners/container: entry point of the sentry container; spawns the app with the prebuilt agent."""

from __future__ import annotations

import threading
from pathlib import Path

from core.host import Host
from core.run.dynamic_drive import drive_coverage
from core.run.workspace import Workspace
from core.runners.adb import Adb

ENV_FILE = Path("/sentry/target/.env")
WORKSPACE_ROOT = Path("/sentry")
AGENT = "/sentry/build/agent.js"


def load_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def main(host: Host | None = None, env_file: Path = ENV_FILE) -> int:
    host = host or Host()
    host.env.update(load_env(env_file))

    host.run_checked(["adb", "connect", "emulator:5555"])
    host.run_checked(["adb", "forward", "tcp:27042", "tcp:27042"])  # frida-server port
    host.run_checked(["adb", "reverse", "tcp:5173", "tcp:5173"])  # web server

    # Same trick as the local runner: drive dynamic coverage concurrently with the (blocking)
    # frida run below, so it lands in the process that run just hooked.
    launcher = threading.Thread(
        target=drive_coverage,
        args=(host, Adb(host), Workspace(WORKSPACE_ROOT), host.env["APP_PACKAGE"], host.getenv("SENTRY_VERBOSE") == "true"),
        daemon=True,
    )
    launcher.start()

    return host.run(["frida", "-H", "127.0.0.1:27042", "-f", host.env["APP_PACKAGE"], "-l", AGENT]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
