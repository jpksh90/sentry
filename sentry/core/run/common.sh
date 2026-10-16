# core/run: shared shell helpers: banner and required-command checks.

print_banner() {
  echo "Sentry - version alpha"
  echo ""
}

check_missing_commands() {
  missing=0

  for cmd in "$@"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "Error: $cmd is not installed"
      missing=$((missing + 1))
    fi
  done

  if [ "$missing" -gt 0 ]; then
    exit 1
  fi
}
