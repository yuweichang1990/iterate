"""Shared test configuration for Auto-Explorer tests.

Provides import_script() for loading scripts with hyphens in their filenames,
and PROJECT_ROOT / SCRIPTS_DIR path constants.
"""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Ensure scripts/ is importable
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def import_script(name):
    """Import a Python script from scripts/ by filename (handles hyphens).

    Usage:
        check_rate_limits = import_script("check-rate-limits.py")
        history = import_script("history.py")
        helpers = import_script("helpers.py")
    """
    module_name = name.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(
        module_name,
        str(SCRIPTS_DIR / name),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
