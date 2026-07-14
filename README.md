# Sentry

Sentry is a dynamic analysis tool for hybrid Android apps. It runs an Android app under Frida, hooks WebView-related APIs, observes JavaScript bridge behavior, and turns the captured event stream into a WebView security report.

The current analysis focuses on:

- WebView settings that increase attack surface
- URL loads, inline content, file URLs, and cleartext traffic
- `addJavascriptInterface` bridge exposure
- JavaScript bridge methods and bridge calls
- WebView permission requests and grants
- Sensitive bridge return values flowing into JavaScript sinks
- Origin-to-bridge mapping for exposed native interfaces

## Repository Layout

- `analyse.sh`: main entry point for running analysis on an APK
- `sentry/hooks/`: Frida hooks injected into the target app
- `sentry/report.py`: report generator for captured Sentry event logs
- `docker-compose.yml`: Linux/KVM Docker analysis environment
- `Benchmark/`: benchmark APKs and source archives
- `scripts/run-benchmarks-linux.sh`: batch runner for benchmark APKs on Linux
- `android/` and `web/`: demonstration Android/WebView target app and web content

## Quick Start

Run Sentry against an APK:

```bash
chmod +x ./analyse.sh
./analyse.sh <APK-FILE> [<APK-PACKAGE>]
```

If the package name is omitted, `analyse.sh` uses `aapt` to extract it from the APK.

Generated outputs:

- `logs/output.log`: raw Frida/Sentry event stream
- `logs/report.md`: human-readable WebView security report
- `target/report.json`: machine-readable report with findings, risk score, evidence, WebView inventory, sensitive data flows, and origin-to-bridge map

## Runner Modes

`analyse.sh` chooses a runner automatically:

- `SENTRY_RUNNER=docker`: uses Docker Compose and the Docker Android emulator. This requires Linux with `/dev/kvm`.
- `SENTRY_RUNNER=local`: uses the host `adb` and `frida` commands with an already-running Android emulator or device.
- `SENTRY_RUNNER=auto`: default. Uses Docker mode on Linux/KVM and local mode elsewhere.

Examples:

```bash
SENTRY_RUNNER=docker ./analyse.sh Benchmark/JsUpdateCaseF.apk com.example.jsUpdatecaseF
SENTRY_RUNNER=local ./analyse.sh Benchmark/JsUpdateCaseF.apk com.example.jsUpdatecaseF
```

Local mode expects:

- `adb` on `PATH`
- `frida` on `PATH`
- a booted Android emulator/device visible to `adb`
- `frida-server` installed on the device, executable, and available at `/data/local/tmp/frida-server` unless `SENTRY_FRIDA_SERVER` is set

Useful local-mode environment variables:

- `SENTRY_ADB_SERIAL`: pass a specific adb device serial
- `SENTRY_FRIDA_DEVICE`: pass a specific Frida device id
- `SENTRY_FRIDA_SERVER`: path to `frida-server` on the Android device
- `SENTRY_BOOT_TIMEOUT`: boot wait timeout in seconds, default `120`

## Run Benchmarks On Linux

The `Benchmark/` folder contains APKs for validating Sentry against known WebView update cases. On a Linux host with Docker Compose, `/dev/kvm`, Python 3, and `aapt`, run:

```bash
scripts/run-benchmarks-linux.sh
```

The script runs every `*.apk` in `Benchmark/`, archives each run, and writes outputs to:

```text
benchmark-results/<apk-name>/
```

Each benchmark result directory may contain:

- `status.txt`: APK path, package name, status, and timeout
- `runner.log`: full stdout/stderr from `analyse.sh`
- `output.log`: captured Sentry event stream
- `logs-output.log`: copy of `logs/output.log`
- `report.json`: machine-readable report, when events were captured
- `report.md`: Markdown report, when events were captured

Benchmark runner options:

```bash
SENTRY_BENCHMARK_SECONDS=900 scripts/run-benchmarks-linux.sh
SENTRY_BENCHMARK_RESULTS=/tmp/sentry-results scripts/run-benchmarks-linux.sh
scripts/run-benchmarks-linux.sh /path/to/benchmark-apks
```

The script intentionally fails early when `/dev/kvm` is unavailable, because Docker emulator mode cannot run correctly without KVM.

## Regenerate Reports

Reports are generated automatically by `analyse.sh`. To regenerate reports from an existing event log:

```bash
python3 sentry/report.py target/output.log \
  --json target/report.json \
  --markdown logs/report.md
```

If you know which WebView origins should be trusted for the target app, pass them explicitly:

```bash
python3 sentry/report.py target/output.log \
  --trusted-origin https://app.example.com \
  --json target/report.json \
  --markdown logs/report.md
```

Trusted origins make bridge exposure and remote-content findings more precise.

## WebTUI Report UI

The `ui/` folder contains a WebTUI-based report viewer for Sentry output. It is a Vite/Vue app that shows report overview metrics, findings, sensitive data flows, the origin-to-bridge map, and the raw JSON report.

Start it locally:

```bash
cd ui
npm install
npm run dev
```

To view a real Sentry report, copy `target/report.json` into `ui/public/report.json` before starting or refreshing the UI:

```bash
cp target/report.json ui/public/report.json
```

If `ui/public/report.json` is missing, the UI starts in sample mode.

## Demonstration App

The repository includes a demonstration WebView app in `android/` and a web target in `web/`. Docker Compose can build the demo APK, start web content, start the Android emulator, install the APK, push `frida-server`, and run Sentry.

```bash
docker compose up
```

The emulator VNC interface is exposed on:

```text
http://localhost:6080
```

## Local Development Setup

This project is developed primarily on Fedora x86_64. Docker mode is intended for Linux hosts with KVM. macOS can use local mode with Android Studio's emulator, `adb`, and `frida-tools`.

Common dependencies:

- `git`
- `docker` and Docker Compose for Docker mode
- `python3`
- `aapt`
- `adb`
- `frida-tools`
- Android SDK tools: `sdkmanager`, `avdmanager`, `emulator`
- Java JDK
- `npm` for the demo web app

Clone the repository:

```bash
git clone git@github.com:jpksh90/sentry.git
cd sentry
```

Build the demo Android APK:

```bash
cd android
./gradlew assembleDebug
./gradlew copyApkToTarget
```

Install or create an emulator:

```bash
sdkmanager "system-images;android-36;google_apis;x86_64"
avdmanager create avd \
  -n android \
  -k "system-images;android-36;google_apis;x86_64" \
  -d "pixel_6"
```

Install Frida tools locally:

```bash
python3 -m pip install frida-tools
```

Install `frida-server` on the emulator:

```bash
curl -L -o frida-server.xz https://github.com/frida/frida/releases/download/17.9.1/frida-server-17.9.1-android-x86_64.xz
unxz frida-server.xz
adb root
adb push frida-server /data/local/tmp/frida-server
adb shell "chmod 755 /data/local/tmp/frida-server"
```

Start the emulator:

```bash
emulator @android
```

Start `frida-server`:

```bash
adb root
adb shell "/data/local/tmp/frida-server >/dev/null 2>&1 &"
```

Run the demo web app:

```bash
cd web
npm install
npm run dev
```

Run Sentry against the demo APK in local mode:

```bash
SENTRY_RUNNER=local ./analyse.sh android/target/app.apk com.example.bachelorproject
```
