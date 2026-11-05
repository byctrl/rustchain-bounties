"""Pytest configuration for the tests/ directory.

Some legacy test modules import `gym`, which has been unmaintained since 2022
and is incompatible with NumPy 2.0. That breaks *collection* of the whole suite
before any test can run, which hides otherwise-passing tests.

Rather than pinning/upgrading dependencies (out of scope here), we simply skip
collecting the affected modules. Remove entries from `collect_ignore` once the
dependency situation is resolved.
"""

import os
import sys

# Make the repository root importable so tests can `import ai_agent` etc.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Paths are relative to this conftest.py (i.e. the tests/ directory).
collect_ignore = [
    # Requires `gym` (unmaintained, incompatible with NumPy 2.0).
    "test_health_check.py",
    # Imports the OpenAI Agents SDK + gym stack; fails at import time.
    "test_openai_agents_rustchain_tool.py",
]
