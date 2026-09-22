"""
data_loader.py — Clean and load IBM AML HI-Small dataset.

Loads Trans.csv, Patterns.txt, and accounts.csv into a single enriched
DataFrame of laundering transactions with pattern labels and entity names.
Exports to Parquet for fast downstream reads.
"""

import re
import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRANS_CSV = PROJECT_ROOT / "HI-Small_Trans.csv"
PATTERNS_TXT = PROJECT_ROOT / "HI-Small_Patterns.txt"
ACCOUNTS_CSV = PROJECT_ROOT / "HI-Small_accounts.csv"
DATA_DIR = PROJECT_ROOT / "data"
PARQUET_OUT = DATA_DIR / "laundering_transactions.parquet"


# 1. Load Trans.csv
def load_transactions(path: Path = TRANS_CSV) -> pd.DataFrame:
    """Load HI-Small_Trans.csv with duplicate Account columns renamed."""
    df = pd.read_csv(
        path,
        dtype={"From Bank": str, "To Bank": str, "Payment Format": str},
        low_memory=False,
    )
    # Columns 3 and 5 are both named 'Account' → pandas loads as Account, Account.1
    if "Account.1" in df.columns:
        df = df.rename(columns={"Account": "From_Account", "Account.1": "To_Account"})
    elif df.columns.tolist().count("Account") == 2:
        cols = df.columns.tolist()
        first_idx = cols.index("Account")
        cols[first_idx] = "From_Account"
        second_idx = cols.index("Account", first_idx + 1)
        cols[second_idx] = "To_Account"
        df.columns = cols
    return df


# 2. Parse Patterns.txt
def parse_patterns(path: Path = PATTERNS_TXT) -> pd.DataFrame:
    """
    Parse HI-Small_Patterns.txt into a DataFrame mapping each laundering
    transaction row to its attempt number and pattern type.

    Format:
        BEGIN LAUNDERING ATTEMPT - PATTERN_TYPE[:  optional degree info]
        <CSV transaction rows>
        END LAUNDERING ATTEMPT - PATTERN_TYPE

    Returns columns: [attempt_id, pattern_type, degree_info, Timestamp,
                      From Bank, From_Account, To Bank, To_Account,
                      Amount Received, Receiving Currency, Amount Paid,
                      Payment Currency, Payment Format, Is Laundering]
    """
    attempts = []
    attempt_counter = 0
    current_pattern = None
    current_degree = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Header: BEGIN LAUNDERING ATTEMPT - PATTERN_TYPE[:  degree info]
            if line.startswith("BEGIN LAUNDERING ATTEMPT"):
                attempt_counter += 1
                # Extract pattern type and optional degree info
                match = re.match(
                    r"BEGIN LAUNDERING ATTEMPT\s*-\s*([\w-]+)(?::\s*(.+))?$", line
                )
                if match:
                    current_pattern = match.group(1).upper()
                    current_degree = match.group(2).strip() if match.group(2) else None
                continue

            # END line
            if line.startswith("END LAUNDERING"):
                current_pattern = None
                current_degree = None
                continue

            # Transaction data line — CSV format
            if current_pattern is not None:
                parts = line.split(",")
                if len(parts) >= 11:
                    attempts.append(
                        {
                            "attempt_id": attempt_counter,
                            "pattern_type": current_pattern,
                            "degree_info": current_degree,
                            "Timestamp": parts[0].strip(),
                            "From Bank": parts[1].strip(),
                            "From_Account": parts[2].strip(),
                            "To Bank": parts[3].strip(),
                            "To_Account": parts[4].strip(),
                            "Amount Received": parts[5].strip(),
                            "Receiving Currency": parts[6].strip(),
                            "Amount Paid": parts[7].strip(),
                            "Payment Currency": parts[8].strip(),
                            "Payment Format": parts[9].strip(),
                            "Is Laundering": parts[10].strip(),
                        }
                    )

    df = pd.DataFrame(attempts)
    if not df.empty:
        df["Amount Received"] = pd.to_numeric(df["Amount Received"], errors="coerce")
        df["Amount Paid"] = pd.to_numeric(df["Amount Paid"], errors="coerce")
        df["Is Laundering"] = pd.to_numeric(df["Is Laundering"], errors="coerce").astype(int)
    return df


# 3. Load accounts.csv
def load_accounts(path: Path = ACCOUNTS_CSV) -> pd.DataFrame:
    """Load HI-Small_accounts.csv for bank name / entity name enrichment."""
    return pd.read_csv(path, dtype=str)


_ACCOUNT_LOOKUP = None


def account_lookup() -> pd.DataFrame:
    """(Bank ID, Account Number) → (Bank Name, Entity Name), loaded once."""
    global _ACCOUNT_LOOKUP
    if _ACCOUNT_LOOKUP is None:
        accounts = load_accounts()
        # Patterns.txt / Trans.csv zero-pad bank IDs ('021174'); accounts.csv doesn't
        accounts["Bank ID"] = accounts["Bank ID"].str.lstrip("0")
        _ACCOUNT_LOOKUP = accounts.drop_duplicates(["Bank ID", "Account Number"]).set_index(
            ["Bank ID", "Account Number"]
        )[["Bank Name", "Entity Name"]]
    return _ACCOUNT_LOOKUP


def enrich_with_accounts(df: pd.DataFrame) -> pd.DataFrame:
    """Add From/To bank and entity names from HI-Small_accounts.csv.

    Works on any frame with `From Bank`/`From_Account`/`To Bank`/`To_Account`
    (the dataset itself or an uploaded IBM-format case). Existing name columns
    are kept where the lookup has no match.
    """
    if not ACCOUNTS_CSV.exists():
        return df
    lookup = account_lookup()
    df = df.copy()
    df["From Bank"] = df["From Bank"].astype(str).str.lstrip("0")
    df["To Bank"] = df["To Bank"].astype(str).str.lstrip("0")
    for side in ("From", "To"):
        found = df[[f"{side} Bank", f"{side}_Account"]].merge(
            lookup, left_on=[f"{side} Bank", f"{side}_Account"], right_index=True, how="left",
        )
        for src_col, dst_col in (("Bank Name", f"{side}_Bank_Name"),
                                 ("Entity Name", f"{side}_Entity_Name")):
            values = found[src_col].values
            if dst_col in df.columns:
                df[dst_col] = pd.Series(values, index=df.index).fillna(df[dst_col])
            else:
                df[dst_col] = values
    return df


# 4. Build enriched laundering DataFrame
def build_enriched_dataset() -> pd.DataFrame:
    """
    Join patterns → accounts to produce the enriched laundering transaction
    dataset with columns:
        attempt_id, pattern_type, Timestamp, From Bank, From_Account,
        From_Bank_Name, From_Entity_Name, To Bank, To_Account,
        To_Bank_Name, To_Entity_Name, Amount Received, Receiving Currency,
        Amount Paid, Payment Currency, Payment Format
    """
    print("Loading Patterns.txt...")
    patterns_df = parse_patterns()
    print(f"  → {len(patterns_df)} laundering transactions across "
          f"{patterns_df['attempt_id'].nunique()} attempts")

    print("Loading accounts.csv...")
    patterns_df = enrich_with_accounts(patterns_df)

    # Drop Is Laundering (always 1 by definition in this subset)
    patterns_df = patterns_df.drop(columns=["Is Laundering"], errors="ignore")

    return patterns_df


def export_parquet(df: pd.DataFrame, path: Path = PARQUET_OUT) -> None:
    """Export the enriched DataFrame to Parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, engine="pyarrow")
    print(f"  → Exported {len(df)} rows to {path}")


# 5. Query interface
def get_attempt(attempt_id: int, parquet_path: Path = PARQUET_OUT) -> pd.DataFrame:
    """Return all transactions for a given laundering attempt."""
    df = pd.read_parquet(parquet_path, engine="pyarrow")
    result = df[df["attempt_id"] == attempt_id]
    if result.empty:
        raise ValueError(
            f"Attempt {attempt_id} not found. "
            f"Valid range: {df['attempt_id'].min()}–{df['attempt_id'].max()}"
        )
    return result


def get_pattern_attempts(pattern_type: str, parquet_path: Path = PARQUET_OUT) -> list[int]:
    """Return all attempt IDs for a given pattern type."""
    df = pd.read_parquet(parquet_path, engine="pyarrow", columns=["attempt_id", "pattern_type"])
    matches = df[df["pattern_type"] == pattern_type.upper()]["attempt_id"].unique().tolist()
    return sorted(matches)


# CLI entry point
if __name__ == "__main__":
    df = build_enriched_dataset()

    # Summary stats
    print("\n── Summary ──")
    print(f"Total laundering transactions: {len(df)}")
    print(f"Unique attempts: {df['attempt_id'].nunique()}")
    print(f"Pattern types: {sorted(df['pattern_type'].unique())}")
    print(f"\nPattern distribution:")
    print(df.groupby("pattern_type")["attempt_id"].nunique().sort_values(ascending=False).to_string())

    # Enrichment check
    from_missing = df["From_Bank_Name"].isna().sum()
    to_missing = df["To_Bank_Name"].isna().sum()
    print(f"\nEnrichment gaps: {from_missing} From + {to_missing} To bank names missing")

    export_parquet(df)
    print("\nDone.")
