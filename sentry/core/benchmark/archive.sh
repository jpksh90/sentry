# core/benchmark: copies one APK's outputs into benchmark-results/<name>/.

archive_outputs() {
  local apk="$1"
  local package="$2"
  local status="$3"
  local runner_log="$4"
  local name
  name="$(basename "$apk" .apk)"

  local out_dir="$RESULTS_DIR/$name"
  mkdir -p "$out_dir"
  rm -f \
    "$out_dir/status.txt" \
    "$out_dir/runner.log" \
    "$out_dir/output.log" \
    "$out_dir/logs-output.log" \
    "$out_dir/report.json" \
    "$out_dir/report.md"

  {
    echo "apk=$apk"
    echo "package=$package"
    echo "status=$status"
    echo "seconds=$RUN_SECONDS"
  } >"$out_dir/status.txt"

  cp "$runner_log" "$out_dir/runner.log"
  [ -f "$ROOT_DIR/target/output.log" ] && cp "$ROOT_DIR/target/output.log" "$out_dir/output.log"
  [ -f "$ROOT_DIR/logs/output.log" ] && cp "$ROOT_DIR/logs/output.log" "$out_dir/logs-output.log"
  [ -f "$ROOT_DIR/target/report.json" ] && cp "$ROOT_DIR/target/report.json" "$out_dir/report.json"
  [ -f "$ROOT_DIR/logs/report.md" ] && cp "$ROOT_DIR/logs/report.md" "$out_dir/report.md"
}
