# core/

Everything that is not instrumentation: the event vocabulary shared by every part, the agent runtime and bundler, orchestration of a run, the runner environments, the report pipeline and the benchmark runner.

| Sub-area | What it holds |
|---|---|
| `events/` | `event_types.json`: **the** event vocabulary. `__init__.py` exposes it to Python as `EventType`. |
| `agent/` | `build_agent.py` bundles `browser/`, `native/` and the agent runtime (`sanitize.js`, `emitter.js`) into one Frida script, in the order given by `manifest.json`. |
| `run/` | `analyse.sh` orchestration: `main.sh` (flow), `common.sh`, `package.sh` (shared `aapt` lookup), `workspace.sh`, `report.sh`. |
| `runners/` | `docker.sh`, `local.sh` + `local_device.sh`, and the in-container scripts under `container/` (`entry.sh`, `frida-server/`). |
| `report/` | The report generator: `loader` → `analyzer` (`tracker` for state, then `rules/` for findings, stored in `findings`) → `assemble` (JSON) and `markdown`; `cli` handles I/O. |
| `benchmark/` | `run.sh` + `preflight.sh`, `run_one.sh`, `archive.sh` (behind `scripts/run-benchmarks-linux.sh`). |

## Where does my change go?

| Change | Where |
|---|---|
| New detection rule | `report/rules/<family>.py`, registered in `report/rules/__init__.py`. Constants go in `report/rules/catalog.py`. |
| Change a finding's severity or text | The detector in `report/rules/` |
| New per-WebView state in the report | `report/tracker.py`, rendered in `report/assemble.py` |
| Report formatting | `report/markdown.py` (Markdown) or `report/assemble.py` (JSON) |
| Report CLI options | `report/cli.py` |
| Local device setup (boot wait, frida-server, adb) | `runners/local_device.sh`, `runners/local.sh` |
| Docker setup | `runners/docker.sh`, `runners/container/`, `../../docker-compose.yml` |
| Input validation, runner selection | `run/main.sh` |
| `aapt` lookup / package name | `run/package.sh` |
| New event type | `events/event_types.json`, emitted from `native/`, consumed in `report/` |
| Bundle contents or order | `agent/manifest.json` |

## Rules

- Detectors (`report/rules/`) never read files or print. Only `report/cli.py` does I/O.
- `report/tracker.py`, `assemble.py` and `markdown.py` never create findings.
- Nothing in `report/` refers to `browser/` or `native/`; the event vocabulary is the only contract between them.
- Size limits: `report/` modules ≤ 340 lines, `run/` and `runners/` scripts ≤ 72 lines, `benchmark/` scripts ≤ 53 lines. Shell under `run/` and `runners/` is POSIX `sh`.
- Before changing anything here, run `python3 -m unittest discover -s tests -t .`. The golden reports in `tests/fixtures/expected/` must stay byte-identical unless a change is meant to alter output.
