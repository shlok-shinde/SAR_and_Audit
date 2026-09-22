"""Tests import the modules the same way the app does: bare names from src/."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture
def northgate_case():
    """The generic-export structuring case with its KYC / alert / investigation."""
    import case_input as ci
    raw = ci.read_table(open(FIXTURES / "generic_structuring.csv", "rb"), "g.csv")
    canon, _, _, _ = ci.import_table(raw, dayfirst=True)
    meta = json.loads((FIXTURES / "generic_structuring_case.json").read_text())
    case = ci.CaseInput.from_dict({**meta, "case_id": "NG-TEST", "source": "upload"})
    case.transactions = canon
    return case
