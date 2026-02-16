#!/usr/bin/env python
"""
Tests that validate bash script syntax using `bash -n`.

Catches syntax errors automatically in CI without running the scripts.
Skips gracefully if bash is not available (e.g., some CI environments).
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def find_git_bash():
    """Find Git Bash on Windows (avoid WSL bash which can't read Windows paths)."""
    if sys.platform != "win32":
        return "bash"
    programfiles = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    candidates = [
        os.path.join(programfiles, "Git", "usr", "bin", "bash.exe"),
        os.path.join(programfiles, "Git", "bin", "bash.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def bash_available():
    bash = find_git_bash() if sys.platform == "win32" else "bash"
    if bash is None:
        return False
    try:
        subprocess.run([bash, "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@unittest.skipUnless(bash_available(), "bash not available")
class TestBashSyntax(unittest.TestCase):
    """Validate bash scripts pass syntax check."""

    def _check_syntax(self, script_path):
        bash = find_git_bash() if sys.platform == "win32" else "bash"
        # Convert to forward-slash path for Git Bash compatibility
        path_str = str(script_path).replace("\\", "/")
        result = subprocess.run(
            [bash, "-n", path_str],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Syntax error in {script_path.name}:\n{result.stderr}",
        )

    def test_setup_script_syntax(self):
        self._check_syntax(PROJECT_ROOT / "scripts" / "setup-auto-explorer.sh")

    def test_stop_hook_syntax(self):
        self._check_syntax(PROJECT_ROOT / "hooks" / "stop-hook.sh")


if __name__ == "__main__":
    unittest.main()
