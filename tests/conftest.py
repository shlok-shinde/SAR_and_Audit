"""Tests import the modules the same way the app does: bare names from src/."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
FIXTURES = ROOT / "tests" / "fixtures"

# The IBM AML dataset is optional and not in the repository (README: "Optional: the IBM
# dataset samples"). Tests that need it skip, rather than fail, in a fresh clone.
IBM_PARQUET = ROOT / "data" / "laundering_transactions.parquet"
IBM_ACCOUNTS = ROOT / "HI-Small_accounts.csv"


@pytest.fixture
def ibm_samples():
    """Skip unless the IBM working set has been built with src/data_loader.py."""
    if not IBM_PARQUET.exists():
        pytest.skip("needs the IBM dataset: download it and run src/data_loader.py (see README)")


@pytest.fixture
def ibm_accounts():
    """Skip unless HI-Small_accounts.csv (bank and entity names) is in the repository root."""
    if not IBM_ACCOUNTS.exists():
        pytest.skip("needs HI-Small_accounts.csv from the IBM dataset (see README)")


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
