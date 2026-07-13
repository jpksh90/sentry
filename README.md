# Sentry
> Security Analysis of Hybrid Android apps

This project aims to evaluate the security implications of hybrid Android apps using dynamic analysis with [Frida](https://frida.re/). The Sentry defines FRIDA hooks that intercept into the app's WebView-related components, also intercepting into JavaScript of the WebView contents.

# Quick Start

Docker emulator mode is supported on Linux distributions with `/dev/kvm`, and so far only tested on Fedora 43. On macOS or hosts without KVM, run a local Android emulator and use local mode instead. You need `aapt` installed with Homebrew if you don't provide the APK package name.

```bash
chmod +x ./analyse.sh
./analyse.sh <APK-FILE> [<APK-PACKAGE>]
```

`analyse.sh` chooses a runner automatically:

- `SENTRY_RUNNER=docker` uses Docker Compose and requires Linux/KVM.
- `SENTRY_RUNNER=local` uses the host `adb` and `frida` commands with an already-running emulator.

## Run Benchmarks On Linux

The `Benchmark/` folder contains APKs for validating Sentry against known WebView update cases. On a Linux host with Docker Compose, `/dev/kvm`, Python 3, and `aapt` available, run:

```bash
scripts/run-benchmarks-linux.sh
```

Results are written to `benchmark-results/<apk-name>/`. The per-APK timeout defaults to 600 seconds and can be changed with `SENTRY_BENCHMARK_SECONDS`.

This outputs a log file and WebView security report:

- `logs/output.log`: raw JSON event stream from the Frida hooks
- `logs/report.md`: human-readable WebView security findings
- `target/report.json`: machine-readable report with risk score, findings, evidence, WebView inventory, sensitive data flows, and an origin-to-bridge map

# WebView Demonstration

We will open source the tool after acceptance of the paper.

```bash
docker compose up
```

The default port for the emulator VNC is `6080`. Visit `localhost:6080` in your browser to view the emulator.

# Setup for Local Development

This project is developed on **Fedora 43** with **x86_64** architecture, so any other configuration is not guaranteed to work.

You'll need the following dependencies installed on your system and be available on your PATH: `git`, `curl`, `unxz`, `python`, `pip`, `adb`, `sdkmanager`, `avdmanager`, `emulator`, `java` (JDK) and `npm`.

## Clone repository

```bash
git clone https://github.com/mathiasyde/bachelorproject
cd bachelorproject
```

Each step from now on assumes your current working directory is in the repository root.

## Build Android APK

```bash
cd android
./gradlew assembleDebug
./gradlew copyApkToTarget
```

This produces an APK file located at `android/target/app.apk`.

## Install Android emulator

Use either Android Studio or use the following bash

```bash
sdkmanager "system-images;android-36;google_apis;x86_64"
avdmanager create avd \
  -n android \
  -k "system-images;android-36;google_apis;x86_64" \
  -d "pixel_6"
```

You can use whatever name or device, but keep the API version recent.

## Install FRIDA on emulator

Firstly install FRIDA tools locally

```bash
pip install frida-tools
```

Then install FRIDA server, this downloads from g

```bash
# the current version of FRIDA is 17.9.1
curl -L -o frida-server.xz https://github.com/frida/frida/releases/download/17.9.1/frida-server-17.9.1-android-x86_64.xz
unxz frida-server.xz
adb root
adb push frida-server /data/local/tmp/
adb shell "chmod 755 /data/local/tmp/frida-server"
```

## Start web server

Run this in another terminal.

```bash
cd web
npm install
npm run dev
```

## Run Frida

Run this in another terminal.

```bash
adb root
adb reverse tcp:5173 tcp:5173 # open for web server
adb shell "/data/local/tmp/frida-server &"
```

## Start emulator

Run this in another terminal.

```bash
emulator @android
```

## Install APK on emulator

Install the APK file from the prior step

```bash
adb install -r android/target/app.apk
```

## Start app on emulator with FRIDA

```bash
frida -U -f com.example.bachelorproject -l sentry/hooks/webview.js -l sentry/hooks/getenv.js
```

You should see output from the FRIDA hooks about WebView activity.

## Generate a WebView Security Report

Reports are generated automatically by `analyse.sh`. You can also regenerate them from an existing log file:

```bash
python3 sentry/report.py target/output.log --json target/report.json --markdown logs/report.md
```

If you know which origins are trusted for the target app, pass them explicitly so bridge exposure and remote-content findings can be scored more accurately:

```bash
python3 sentry/report.py target/output.log \
  --trusted-origin https://app.example.com \
  --json target/report.json \
  --markdown logs/report.md
```

The report includes an **Origin To Bridge Map** section that groups each observed JavaScript bridge by WebView origin, exposed methods, and bridge calls.
It also includes a **Sensitive Data Flows** section when values returned by sensitive-looking bridge methods reach JavaScript sinks such as `fetch`, XHR, `sendBeacon`, navigation APIs, `postMessage`, `eval`, or storage.

## WebTUI Report Interface

The `/tui` folder contains a standalone WebTUI-based report viewer for Sentry output. It is separate from the `/web` demo app, so the demo remains a target for WebView analysis.

```bash
cd tui
npm install
npm run dev
```

To view a real report, copy or serve `target/report.json` as `tui/public/report.json`; otherwise the interface starts with sample data.
