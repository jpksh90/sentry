#!/usr/bin/env bash
# core/benchmark: runs every benchmark APK through analyse.sh on Linux (sourced by scripts/run-benchmarks-linux.sh).
set -u -o pipefail

ROOT_DIR="${SENTRY_ROOT:?SENTRY_ROOT must be set by the launcher}"
BENCHMARK_DIR="${SENTRY_BENCHMARK_DIR:-}"
RESULTS_DIR="${SENTRY_BENCHMARK_RESULTS:-"$ROOT_DIR/benchmark-results"}"
RUN_SECONDS="${SENTRY_BENCHMARK_SECONDS:-600}"

. "$ROOT_DIR/sentry/core/run/package.sh"
. "$ROOT_DIR/sentry/core/benchmark/preflight.sh"
. "$ROOT_DIR/sentry/core/benchmark/archive.sh"
. "$ROOT_DIR/sentry/core/benchmark/run_one.sh"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ -n "${1:-}" ]; then
  BENCHMARK_DIR="$1"
elif [ -z "$BENCHMARK_DIR" ]; then
  if [ -d "$ROOT_DIR/Benchmark" ]; then
    BENCHMARK_DIR="$ROOT_DIR/Benchmark"
  else
    BENCHMARK_DIR="$ROOT_DIR/benchmarks"
  fi
fi

check_preconditions

mkdir -p "$RESULTS_DIR"

shopt -s nullglob
apks=("$BENCHMARK_DIR"/*.apk)
shopt -u nullglob
[ "${#apks[@]}" -gt 0 ] || die "no APK files found in $BENCHMARK_DIR"

for apk in "${apks[@]}"; do
  package="$(apk_package_name "$apk")"
  [ -n "$package" ] || die "could not extract package name from $apk"
  run_one "$apk" "$package"
done

if [ "${SENTRY_KEEP_CONTAINERS:-0}" != "1" ]; then
  (cd "$ROOT_DIR" && docker compose down >/dev/null 2>&1) || true
fi
