#!/bin/sh
# core launcher: keeps ./analyse.sh working; the orchestration lives in sentry/core/run/.

SENTRY_HOME="$(dirname "$0")/sentry"
. "$SENTRY_HOME/core/run/main.sh"

sentry_analyse "$@"
