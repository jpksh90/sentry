# core/runners: local runner: host adb/frida against a running emulator or device; builds and loads the agent.

run_local() {
  check_missing_commands adb frida

  echo "Using local emulator mode"
  if [ "$KVM_AVAILABLE" -ne 1 ]; then
    echo "Docker/KVM is unavailable; using the host Android emulator via adb."
  fi

  if ! adb_cmd get-state >/dev/null 2>&1; then
    echo "Error: no Android emulator/device is visible to adb."
    echo "Start an emulator first, or set SENTRY_RUNNER=docker on a Linux host with /dev/kvm."
    exit 1
  fi

  wait_for_boot

  echo "Installing APK..."
  adb_cmd install -r ./target/app.apk
  adb_cmd reverse tcp:5173 tcp:5173 >/dev/null 2>&1 || true

  ensure_frida_server

  if ! python3 ./sentry/core/agent/build_agent.py --out ./target/agent.js; then
    echo "Error: failed to build Sentry agent"
    exit 1
  fi

  if [ "${SENTRY_FRIDA_DEVICE:-}" != "" ]; then
    frida -D "$SENTRY_FRIDA_DEVICE" -f "$APP_PACKAGE" \
      -l ./target/agent.js \
      | tee ./target/output.log ./logs/output.log
  else
    frida -U -f "$APP_PACKAGE" \
      -l ./target/agent.js \
      | tee ./target/output.log ./logs/output.log
  fi
}
