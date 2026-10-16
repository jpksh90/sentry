# core/run: generates the reports once, on exit, if any Sentry events were captured.

REPORT_GENERATED=0

generate_report() {
  if [ "$REPORT_GENERATED" -eq 1 ]; then
    return
  fi
  REPORT_GENERATED=1

  if [ -s ./target/output.log ]; then
    python3 ./sentry/report.py ./target/output.log \
      --json ./target/report.json \
      --markdown ./logs/report.md || true
  else
    echo "Report skipped: no Sentry events were captured"
  fi
}
