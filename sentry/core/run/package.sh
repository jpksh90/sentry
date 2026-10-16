# core/run: the one shared aapt lookup and APK package-name parser (used by analyse.sh and the benchmark runner).
# POSIX sh; sourced by both sh and bash. SENTRY_AAPT_FALLBACKS is internal (tests only).

find_aapt() {
  if command -v aapt >/dev/null 2>&1; then
    command -v aapt
    return 0
  fi

  aapt_sdk_root="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
  if [ -n "$aapt_sdk_root" ] && [ -d "$aapt_sdk_root/build-tools" ]; then
    aapt_candidate=$(find "$aapt_sdk_root/build-tools" -maxdepth 2 -type f -name aapt -perm -111 \
      | sort -V \
      | tail -n 1)
    if [ -n "$aapt_candidate" ]; then
      echo "$aapt_candidate"
      return 0
    fi
  fi

  for aapt_candidate in ${SENTRY_AAPT_FALLBACKS:-/opt/homebrew/bin/aapt /usr/local/bin/aapt}; do
    if [ -x "$aapt_candidate" ]; then
      echo "$aapt_candidate"
      return 0
    fi
  done

  return 1
}

# Prints the package name of APK $1 using $AAPT_BIN.
apk_package_name() {
  "$AAPT_BIN" dump badging "$1" \
    | sed -n "s/^package: name='\([^']*\)'.*/\1/p" \
    | head -n 1
}
