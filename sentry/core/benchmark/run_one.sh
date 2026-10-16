# core/benchmark: runs one APK through analyse.sh under a timeout and maps the exit code to a status.

run_one() {
  local apk="$1"
  local package="$2"
  local log_file
  local status
  local rc

  log_file="$(mktemp)"
  echo "==> $(basename "$apk") ($package)"

  (
    cd "$ROOT_DIR" || exit 1
    SENTRY_RUNNER=docker timeout -s INT "$RUN_SECONDS" ./analyse.sh "$apk" "$package"
  ) >"$log_file" 2>&1
  rc=$?

  if [ "$rc" -eq 0 ]; then
    status="completed"
  elif [ "$rc" -eq 124 ] || [ "$rc" -eq 130 ]; then
    status="timed_out"
  else
    status="failed_$rc"
  fi

  archive_outputs "$apk" "$package" "$status" "$log_file"
  rm -f "$log_file"
  echo "<== $(basename "$apk"): $status"
}
