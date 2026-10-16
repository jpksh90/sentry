#!/usr/bin/env bash
# core launcher: keeps scripts/run-benchmarks-linux.sh working; the runner lives in sentry/core/benchmark/.

SENTRY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$SENTRY_ROOT/sentry/core/benchmark/run.sh"
