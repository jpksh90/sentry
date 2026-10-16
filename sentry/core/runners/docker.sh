# core/runners: Docker Compose runner: emulator, frida-server and sentry containers on a Linux/KVM host.

run_docker() {
  check_missing_commands docker

  if [ "$KVM_AVAILABLE" -ne 1 ]; then
    echo "Error: Docker emulator mode requires /dev/kvm."
    echo "Use SENTRY_RUNNER=local with a running Android emulator on macOS or hosts without KVM."
    exit 1
  fi

  docker compose down
  docker compose up -d emulator run-frida-server sentry

  docker logs -f sentry | tee ./target/output.log ./logs/output.log
}
