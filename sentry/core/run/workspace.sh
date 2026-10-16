# core/run: prepares target/ and logs/ for one analysis run (APK copy, empty event log, .env).

prepare_workspace() {
  mkdir -p ./target
  mkdir -p ./logs
  cp "$APK_INPUT" ./target/app.apk
  touch ./target/output.log
  rm -f ./target/report.json ./logs/report.md
  echo "APP_PACKAGE=$APP_PACKAGE" > ./target/.env
}
