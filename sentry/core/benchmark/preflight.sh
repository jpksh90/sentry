# core/benchmark: usage text, error helpers and host preconditions for the benchmark runner.

usage() {
  cat <<USAGE
Usage: $(basename "$0") [benchmark-dir]

Runs every APK in the benchmark directory through analyse.sh on Linux.

Environment:
  SENTRY_BENCHMARK_SECONDS   Per-APK timeout in seconds (default: 600)
  SENTRY_BENCHMARK_RESULTS   Output directory (default: benchmark-results)
  SENTRY_BENCHMARK_DIR       Benchmark directory override
USAGE
}

die() {
  echo "Error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is not installed"
}

check_preconditions() {
  [ "$(uname -s)" = "Linux" ] || die "this benchmark runner is intended for Linux"
  [ -c /dev/kvm ] || die "/dev/kvm is required for Docker emulator mode"
  [ -d "$BENCHMARK_DIR" ] || die "benchmark directory not found: $BENCHMARK_DIR"

  require_command docker
  require_command timeout
  require_command python3
  docker compose version >/dev/null 2>&1 || die "docker compose is not available"

  AAPT_BIN="$(find_aapt)"
  [ -n "$AAPT_BIN" ] || die "aapt is required on PATH or under ANDROID_HOME/ANDROID_SDK_ROOT"
}
