# core/

Everything that is not instrumentation: the event vocabulary shared by every part, the agent runtime and bundler, orchestration of a run, the runner environments, the report pipeline and the benchmark runner.

| Sub-area | What it holds |
|---|---|
| `events/` | `event_types.json`: **the** event vocabulary. `__init__.py` exposes it to Python as `EventType`. |
| `agent/` | `build_agent.py` bundles `browser/`, `native/` and the agent runtime (`sanitize.js`, `emitter.js`) into one Frida script, in the order given by `manifest.json`. |
| `host.py` | **Facade** over the OS: environment, `PATH` lookups, platform/KVM detection, processes and `tee` pipelines. Nothing else in `core/` calls `subprocess`, so tests can swap in a fake host. |
| `run/` | `analyse.sh` orchestration. `session.py` holds `AnalysisSession`, a **template method** with fixed steps (validate → resolve package → choose runner → preflight → prepare workspace → run → report on exit). Also `package.py` (shared `aapt` lookup), `workspace.py` and `reporting.py`. |
| `runners/` | **Strategy**: `Runner` (`base.py`) with `DockerRunner` and `LocalRunner`, chosen by the factory `select_runner()` in `__init__.py`. `adb.py` is the adb adapter (serial, boot wait, frida-server). `container/` holds the Python entry points of the `sentry` and `run-frida-server` containers and the frida-server Dockerfile. |
| `report/` | The report generator: `loader` → `analyzer` (`tracker` for state, then `rules/` for findings, stored in `findings`) → `assemble` (JSON) and `markdown`; `cli` handles I/O. |
| `benchmark/` | `BenchmarkSuite` in `suite.py` (preflight, one timed `analyse.sh` run per APK, result archive), behind `scripts/run-benchmarks-linux.sh`. |

## Where does my change go?

| Change | Where |
|---|---|
| New detection rule | `report/rules/<family>.py`, registered in `report/rules/__init__.py`. Constants go in `report/rules/catalog.py`. |
| Change a finding's severity or text | The detector in `report/rules/` |
| New per-WebView state in the report | `report/tracker.py`, rendered in `report/assemble.py` |
| Report formatting | `report/markdown.py` (Markdown) or `report/assemble.py` (JSON) |
| Report CLI options | `report/cli.py` |
| Local device setup (boot wait, frida-server, adb) | `runners/adb.py`, `runners/local.py` |
| Docker setup | `runners/docker.py`, `runners/container/`, `../../docker-compose.yml` |
| A new way to run the app (e.g. a device farm) | A new `Runner` subclass in `runners/`, registered in `RUNNERS` in `runners/__init__.py` |
| Input validation, step order | `run/session.py` |
| `aapt` lookup / package name | `run/package.py` |
| New event type | `events/event_types.json`, emitted from `native/`, consumed in `report/` |
| Bundle contents or order | `agent/manifest.json` |

## Rules

- Detectors (`report/rules/`) never read files or print. Only `report/cli.py` does I/O.
- `report/tracker.py`, `assemble.py` and `markdown.py` never create findings.
- Nothing in `report/` refers to `browser/` or `native/`; the event vocabulary is the only contract between them.
- Orchestration is Python. The only shell scripts are the root launchers `analyse.sh` and `scripts/run-benchmarks-linux.sh`, which hand off to `python3 -m core.run` and `python3 -m core.benchmark`.
- Only `host.py` runs processes. Runners print an error and exit with `host.die(...)`, which works like a failing shell script: the report-on-exit step still runs.
- Size limits: `report/` modules ≤ 340 lines, `run/` and `runners/` modules ≤ 100 lines, `benchmark/` and `host.py` ≤ 160 lines.
- Before changing anything here, run `python3 -m unittest discover -s tests -t .`. The golden reports in `tests/fixtures/expected/` must stay byte-identical unless a change is meant to alter output.
