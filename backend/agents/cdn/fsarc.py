"""
FSARC Service Wrapper (FINAL FIX – correct package root)
-------------------------------------------------------
Compatible with nested FSARC/FSARC structure.
"""

import sys
from pathlib import Path
from typing import Dict, List

import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent

# Path that contains rules.yml and dict.yml
FSARC_ROOT = CURRENT_DIR / "FSARC"

if not (FSARC_ROOT / "rules.yml").exists():
    raise RuntimeError(f"rules.yml not found in {FSARC_ROOT}")

# Make FSARC importable (no global chdir; config.py now uses absolute paths)
sys.path.insert(0, str(FSARC_ROOT))


# -------------------------------------------------
# 1. Resolve FSARC package root CORRECTLY
# -------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent

# This is the directory that CONTAINS the inner FSARC package
FSARC_PACKAGE_ROOT = CURRENT_DIR / "FSARC"

if not FSARC_PACKAGE_ROOT.exists():
    raise RuntimeError(
        f"FSARC package root not found at {FSARC_PACKAGE_ROOT}"
    )

# CRITICAL: add THIS directory to sys.path
# so `import FSARC.*` works inside API.py
sys.path.insert(0, str(FSARC_PACKAGE_ROOT))

# -------------------------------------------------
# 2. Now FSARC internal imports will resolve
# -------------------------------------------------

from FSARC.API import ConflictDetector
from FSARC.modelling import model
from FSARC.detection import Detector
from FSARC.Requirement import Req


class FSARCService:
    """
    Agent-safe FSARC wrapper
    """

    _started = False

    def __init__(self):
        if not FSARCService._started:
            ConflictDetector.start()
            FSARCService._started = True

    def check(self, req1: str, req2: str) -> Dict:
        """
        Detect semantic conflict between two requirements.
        """

        modelled_reqs: List[Req] = []
        rid = 1

        for text in (req1, req2):
            for r in model(text):
                r.reqid = rid
                rid += 1
                modelled_reqs.append(r)

        if len(modelled_reqs) < 2:
            return {"is_conflict": False}

        conflicts = Detector.detect(modelled_reqs)

        if not conflicts:
            return {"is_conflict": False}

        conflict_type, reqs = conflicts[0]

        return {
            "is_conflict": True,
            "conflict_type": str(conflict_type),
            "requirements": [str(r) for r in reqs]
        }

    @staticmethod
    def shutdown():
        if FSARCService._started:
            ConflictDetector.close()
            FSARCService._started = False
