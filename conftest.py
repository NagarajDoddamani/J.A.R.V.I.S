"""JARVIS test conftest.

Adds the repository root to ``sys.path`` so test modules can import
``backend.*`` and ``shared.*`` without requiring an installable layout.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
