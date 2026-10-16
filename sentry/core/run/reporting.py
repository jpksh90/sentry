"""core/run: generate the reports exactly once when a run ends, however it ends (replaces the shell EXIT trap)."""

from __future__ import annotations

import traceback
from contextlib import contextmanager
from typing import Iterator

from core.host import Host
from core.report import cli as report_cli
from core.run.workspace import Workspace


def generate_report(host: Host, workspace: Workspace) -> None:
    if workspace.output_log.is_file() and workspace.output_log.stat().st_size > 0:
        try:
            report_cli.main(
                [str(workspace.output_log), "--json", str(workspace.report_json), "--markdown", str(workspace.report_md)]
            )
        except SystemExit:
            pass
        except Exception:  # a failed report must not mask the run's own exit status
            traceback.print_exc()
    else:
        host.echo("Report skipped: no Sentry events were captured")


@contextmanager
def report_on_exit(host: Host, workspace: Workspace) -> Iterator[None]:
    try:
        yield
    finally:
        generate_report(host, workspace)
