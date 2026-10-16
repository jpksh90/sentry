# Sentry

Sentry is a dynamic analysis tool for hybrid Android apps. It runs an APK under Frida, hooks Android WebView APIs, observes JavaScript bridge behavior, and generates WebView security reports.

Use `analyse.sh` as the entry point for analysis.

```bash
./analyse.sh <APK-FILE> [<APK-PACKAGE>]
```


## Quick Start

Make the entry point executable:

```bash
chmod +x ./analyse.sh
```

Run an APK when you know the package name:

```bash
./analyse.sh path/to/app.apk com.example.app
```

Run an APK and let Sentry extract the package name:

```bash
./analyse.sh path/to/app.apk
```

Package extraction requires `aapt`. It is looked up on `PATH`, then in the newest `$ANDROID_HOME` (or `$ANDROID_SDK_ROOT`) `build-tools/` directory, then at `/opt/homebrew/bin/aapt` or `/usr/local/bin/aapt`.

## Outputs

`analyse.sh` writes all analysis artifacts automatically:

- `logs/output.log`: raw Sentry event stream captured from Frida
- `logs/report.md`: human-readable WebView security report
- `target/output.log`: raw event stream copy used for report generation
- `target/report.json`: machine-readable report with risk score, findings, evidence, WebView inventory, sensitive data flows, and origin-to-bridge map

If no Sentry events are captured, report generation is skipped so empty runs are not mistaken for clean results.

## Project layout

The analysis toolchain lives under `sentry/`, in three areas:

| Directory | What goes there |
|---|---|
| [`sentry/browser/`](sentry/browser/README.md) | Code that runs **inside WebView pages**: the in-page observer, bridge-taint wrappers and the probe. |
| [`sentry/native/`](sentry/native/README.md) | Frida hooks **in the app process**, one module per Android API family (lifecycle, settings, clients, JS bridge, JS evaluation, permissions, environment). |
| [`sentry/core/`](sentry/core/README.md) | Everything else: the event vocabulary, the agent bundler, `analyse.sh` orchestration, the Docker and local runners, the report generator and the benchmark runner. |

`analyse.sh`, `scripts/run-benchmarks-linux.sh` and `sentry/report.py` are thin launchers into `sentry/core/`. The Frida agent is built from all three areas into a single script by `sentry/core/agent/build_agent.py`. The local runner does this on every run, and the Docker image does it at build time.

Run the test suite with:

```bash
python3 -m unittest discover -s tests -t .
```

## Runner Modes

`analyse.sh` selects a runner with `SENTRY_RUNNER`.

```bash
SENTRY_RUNNER=auto ./analyse.sh path/to/app.apk com.example.app
SENTRY_RUNNER=docker ./analyse.sh path/to/app.apk com.example.app
SENTRY_RUNNER=local ./analyse.sh path/to/app.apk com.example.app
```

Modes:

- `auto`: default. Uses Docker mode on Linux when `/dev/kvm` exists, otherwise local mode.
- `docker`: uses the Docker Compose Android emulator environment. Requires Linux and `/dev/kvm`.
- `local`: uses a host Android emulator or device through local `adb` and `frida`.

## Linux Docker Mode

Use Docker mode on Linux hosts with KVM:

```bash
SENTRY_RUNNER=docker ./analyse.sh Benchmark/JsUpdateCaseF.apk com.example.jsUpdatecaseF
```

Requirements:

- Linux with `/dev/kvm`
- Docker and Docker Compose
- Python 3
- `aapt`, unless the package name is passed explicitly

`analyse.sh` starts the required Docker services, installs the APK, starts Frida, captures Sentry events, and generates reports.

## Local Mode

Use local mode on macOS, Linux without Docker emulator support, or when you already have an emulator/device running:

```bash
SENTRY_RUNNER=local ./analyse.sh Benchmark/JsUpdateCaseF.apk com.example.jsUpdatecaseF
```

Requirements:

- `adb` on `PATH`
- `frida` on `PATH`
- a booted Android emulator or device visible to `adb`
- `frida-server` installed and executable on the Android device

Local-mode environment variables:

- `SENTRY_ADB_SERIAL`: adb serial for a specific emulator/device
- `SENTRY_FRIDA_DEVICE`: Frida device id
- `SENTRY_FRIDA_SERVER`: device path to `frida-server`, default `/data/local/tmp/frida-server`
- `SENTRY_BOOT_TIMEOUT`: emulator boot wait timeout in seconds, default `120`

Example with a specific adb device:

```bash
SENTRY_RUNNER=local \
SENTRY_ADB_SERIAL=emulator-5554 \
./analyse.sh path/to/app.apk com.example.app
```

## Benchmarks

The `Benchmark/` directory contains benchmark APKs for known WebView update cases. Run each benchmark through the same entry point:

```bash
./analyse.sh Benchmark/JSUpdateCaseD.apk com.example.jsUpdatecaseD
./analyse.sh Benchmark/JsUpdateCaseE.apk com.example.jsUpdatecaseE
./analyse.sh Benchmark/JsUpdateCaseF.apk com.example.jsUpdatecaseF
./analyse.sh Benchmark/JsUpdateCaseG.apk com.example.jsUpdatecaseG
./analyse.sh Benchmark/strongUpdate.apk com.example.strongupdate
./analyse.sh Benchmark/strongUpdatecaseA.apk com.example.strongupdate
./analyse.sh Benchmark/strongUpdatecaseB.apk com.example.strongupdatecaseb
./analyse.sh Benchmark/strongUpdatecaseC.apk com.example.strongupdatecaseC
```

To run all benchmark APKs on a Linux/KVM machine:

```bash
for apk in Benchmark/*.apk; do
  ./analyse.sh "$apk"
done
```

Pass package names explicitly when `aapt` is unavailable.

## Demo APK

The repository includes a demonstration Android/WebView app under `android/` and web content under `web/`. After building the demo APK, analyze it through the same entry point:

```bash
./analyse.sh android/target/app.apk com.example.bachelorproject
```

## Troubleshooting

`Error: Docker emulator mode requires /dev/kvm.`

Use a Linux host with KVM for Docker mode, or use local mode with a host emulator:

```bash
SENTRY_RUNNER=local ./analyse.sh path/to/app.apk com.example.app
```

`Error: adb is not installed` or `Error: frida is not installed`

Install Android platform tools and Frida tools, then rerun `analyse.sh`.

`Error: frida-server was not found`

Install `frida-server` on the Android device or set `SENTRY_FRIDA_SERVER` to the correct device path.

`Failed to find aapt`

Pass the package name explicitly:

```bash
./analyse.sh path/to/app.apk com.example.app
```

or install `aapt` so `analyse.sh` can extract it automatically.

Docker mode still runs old hooks after updating Sentry

An existing `sentry` image keeps the agent it was built with. Rebuild the images after updating:

```bash
docker compose build sentry run-frida-server
```
