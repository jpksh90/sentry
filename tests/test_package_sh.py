"""The shared package helper finds aapt in one documented order and parses the package name strictly (FR-014)."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import SENTRY_DIR

PACKAGE_SH = SENTRY_DIR / "core" / "run" / "package.sh"
BADGING = "package: name='com.x' versionCode='1'\nsdkVersion:'21'\nuses-permission: name='a.package.b'\n"


def fake_aapt(path: Path, output: str = BADGING) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\ncat <<'OUT'\n{output}OUT\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def run_sh(script: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(["sh", "-c", f'. "{PACKAGE_SH}"\n{script}'], env=env, capture_output=True, text=True)


class FindAapt(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.base_path = "/usr/bin:/bin"
        self.missing = str(self.root / "nope" / "aapt")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        return {"PATH": self.base_path, "SENTRY_AAPT_FALLBACKS": self.missing, **extra}

    def test_path_first(self) -> None:
        on_path = fake_aapt(self.root / "bin" / "aapt")
        sdk = self.root / "sdk"
        fake_aapt(sdk / "build-tools" / "34.0.0" / "aapt")
        result = run_sh("find_aapt", self.env(PATH=f"{on_path.parent}:{self.base_path}", ANDROID_HOME=str(sdk)))
        self.assertEqual(result.stdout.strip(), str(on_path))

    def test_newest_sdk_build_tools(self) -> None:
        sdk = self.root / "sdk"
        for version in ("9.0.0", "30.0.3", "34.0.0"):
            fake_aapt(sdk / "build-tools" / version / "aapt")
        result = run_sh("find_aapt", self.env(ANDROID_HOME=str(sdk)))
        self.assertEqual(result.stdout.strip(), str(sdk / "build-tools" / "34.0.0" / "aapt"))

    def test_android_sdk_root_used_when_home_unset(self) -> None:
        sdk = self.root / "sdk-root"
        fake_aapt(sdk / "build-tools" / "33.0.1" / "aapt")
        result = run_sh("find_aapt", self.env(ANDROID_SDK_ROOT=str(sdk)))
        self.assertEqual(result.stdout.strip(), str(sdk / "build-tools" / "33.0.1" / "aapt"))

    def test_fallback_paths_last(self) -> None:
        fallback = fake_aapt(self.root / "brew" / "aapt")
        empty_sdk = self.root / "empty-sdk" / "build-tools"
        empty_sdk.mkdir(parents=True)
        result = run_sh(
            "find_aapt",
            self.env(ANDROID_HOME=str(empty_sdk.parent), SENTRY_AAPT_FALLBACKS=f"{self.missing} {fallback}"),
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), str(fallback))

    def test_not_found(self) -> None:
        result = run_sh("find_aapt", self.env())
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")


class ApkPackageName(unittest.TestCase):
    def test_strict_single_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aapt = fake_aapt(Path(tmp) / "aapt")
            result = run_sh('AAPT_BIN="$FAKE"; apk_package_name some.apk', {"PATH": "/usr/bin:/bin", "FAKE": str(aapt)})
        self.assertEqual(result.stdout, "com.x\n")


if __name__ == "__main__":
    unittest.main()
