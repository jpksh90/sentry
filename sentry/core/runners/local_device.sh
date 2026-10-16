# core/runners: device helpers for the local runner: adb wrapper, boot wait and frida-server startup.

adb_cmd() {
  if [ "${SENTRY_ADB_SERIAL:-}" != "" ]; then
    adb -s "$SENTRY_ADB_SERIAL" "$@"
  else
    adb "$@"
  fi
}

wait_for_boot() {
  boot_wait="${SENTRY_BOOT_TIMEOUT:-120}"
  while [ "$boot_wait" -gt 0 ]; do
    if [ "$(adb_cmd shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; then
      break
    fi
    sleep 2
    boot_wait=$((boot_wait - 2))
  done

  if [ "$boot_wait" -le 0 ]; then
    echo "Error: Android emulator did not finish booting within ${SENTRY_BOOT_TIMEOUT:-120}s"
    exit 1
  fi
}

ensure_frida_server() {
  frida_server="${SENTRY_FRIDA_SERVER:-/data/local/tmp/frida-server}"
  if ! adb_cmd shell "test -x '$frida_server'" >/dev/null 2>&1; then
    echo "Error: frida-server was not found at $frida_server on the emulator."
    echo "Install it first, or set SENTRY_FRIDA_SERVER to the correct device path."
    exit 1
  fi

  if ! adb_cmd shell "pgrep -f '$frida_server' >/dev/null 2>&1"; then
    echo "Starting frida-server..."
    adb_cmd shell "$frida_server >/dev/null 2>&1 &"
    sleep 2
  fi
}
