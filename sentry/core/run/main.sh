# core/run: analysis orchestration: validate input -> resolve package -> pick runner -> prepare workspace -> run.
# Sourced by analyse.sh with SENTRY_HOME set; expects to run from the repository root.

. "$SENTRY_HOME/core/run/common.sh"
. "$SENTRY_HOME/core/run/package.sh"
. "$SENTRY_HOME/core/run/workspace.sh"
. "$SENTRY_HOME/core/run/report.sh"
. "$SENTRY_HOME/core/runners/docker.sh"
. "$SENTRY_HOME/core/runners/local_device.sh"
. "$SENTRY_HOME/core/runners/local.sh"

sentry_analyse() {
  print_banner

  KVM_AVAILABLE=0
  if [ -c /dev/kvm ]; then
    KVM_AVAILABLE=1
  fi

  check_missing_commands python3
  APK_INPUT="$1"
  if [ "$APK_INPUT" = "" ]; then
    echo "Usage: $0 <apk> [<apk-package>]"
    exit 1
  fi
  if [ ! -f "$APK_INPUT" ]; then
    echo "File not found: $APK_INPUT"
    exit 1
  fi

  APP_PACKAGE="$2"
  if [ "$APP_PACKAGE" = "" ]; then
    AAPT_BIN=$(find_aapt)
    if [ "$AAPT_BIN" = "" ]; then
      echo "Failed to find aapt. Install it with Homebrew or provide the APK package name."
      exit 1
    fi
    APP_PACKAGE=$(apk_package_name "$APK_INPUT")
  fi
  if [ "$APP_PACKAGE" = "" ]; then
    echo "Failed to extract package name from apk"
    exit 1
  fi

  RUNNER="${SENTRY_RUNNER:-auto}"
  case "$RUNNER" in
    auto)
      if [ "$(uname -s)" = "Linux" ] && [ "$KVM_AVAILABLE" -eq 1 ]; then RUNNER=docker; else RUNNER=local; fi
      ;;
    docker|local) ;;
    *)
      echo "Error: invalid SENTRY_RUNNER '$RUNNER' (expected auto, docker, or local)"
      exit 1
      ;;
  esac

  if [ "$RUNNER" = "docker" ] && [ ! -f docker-compose.yml ]; then
    echo "Error: docker-compose.yml not found"
    exit 1
  fi

  prepare_workspace

  trap generate_report EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  case "$RUNNER" in
    docker) run_docker ;;
    local) run_local ;;
  esac
}
