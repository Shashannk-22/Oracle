# =============================================================================
# report_handler.py
# Handles all Excel reading, validation, splitting, and output report writing.
# The main script never touches pandas directly — it all goes through here.
# =============================================================================

import pandas as pd
import logging
from pathlib import Path
from config import (
    FILE_PATH, OUTPUT_REPORT_PATH,
    COL_ACCOUNT_TYPE, COL_USERNAME, COL_FULLNAME, COL_ENVIRONMENT, COL_TARGET,
    USER_ACCOUNT_VALUE, SERVICE_ACCOUNT_VALUE
)

logger = logging.getLogger(__name__)

# All columns we expect to exist in the spreadsheet
REQUIRED_COLUMNS = [COL_ACCOUNT_TYPE, COL_USERNAME, COL_FULLNAME, COL_ENVIRONMENT]


def load_and_validate() -> pd.DataFrame:
    """
    Reads the fallout report Excel file.
    Validates that all required columns exist.
    Raises clear errors if file is missing or malformed.
    Returns the full raw dataframe.
    """
    path = Path(FILE_PATH)

    if not path.exists():
        raise FileNotFoundError(
            f"Fallout report not found at: {FILE_PATH}\n"
            f"Please update FILE_PATH in your .env file."
        )

    logger.info(f"Loading fallout report from: {FILE_PATH}")
    df = pd.read_excel(path)
    logger.info(f"Loaded {len(df)} total rows.")

    # Validate required columns exist
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"The following required columns are missing from the spreadsheet:\n"
            f"  {missing_cols}\n"
            f"Available columns are: {list(df.columns)}"
        )

    # Drop rows where account type is blank — can't process them
    before = len(df)
    df = df[df[COL_ACCOUNT_TYPE].notna()]
    dropped = before - len(df)
    if dropped > 0:
        logger.warning(f"Dropped {dropped} rows with blank account type.")

    return df


def split_accounts(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits the dataframe into user accounts and service accounts.
    Logs counts for both. Returns (user_df, service_df).
    """
    user_df    = df[df[COL_ACCOUNT_TYPE] == USER_ACCOUNT_VALUE].copy()
    service_df = df[df[COL_ACCOUNT_TYPE] == SERVICE_ACCOUNT_VALUE].copy()

    logger.info(f"User accounts found:    {len(user_df)}")
    logger.info(f"Service accounts found: {len(service_df)}")

    unrecognised = df[
        ~df[COL_ACCOUNT_TYPE].isin([USER_ACCOUNT_VALUE, SERVICE_ACCOUNT_VALUE])
    ]
    if len(unrecognised) > 0:
        logger.warning(
            f"{len(unrecognised)} rows had unrecognised account type values: "
            f"{unrecognised[COL_ACCOUNT_TYPE].unique().tolist()} — skipped."
        )

    return user_df, service_df


def get_user_dataframe(user_df: pd.DataFrame, username: str) -> pd.DataFrame:
    """
    Returns a filtered, display-ready dataframe for a single user.
    Selects only the columns that should appear in the email table.
    """
    cols = [c for c in [COL_ENVIRONMENT, COL_TARGET, COL_USERNAME] if c in user_df.columns]
    return (
        user_df[user_df[COL_USERNAME] == username]
        .reset_index(drop=True)[cols]
    )


def get_first_name(user_df: pd.DataFrame, username: str) -> str:
    """
    Extracts the first name from tbFullnameData for email greeting.
    Handles 'LastName, FirstName' format safely.
    Falls back to username if name is missing or unparseable.
    """
    try:
        full_name = user_df[user_df[COL_USERNAME] == username].iloc[0][COL_FULLNAME]
        if pd.isna(full_name) or not isinstance(full_name, str):
            return username
        # Format: "Doe, John" → "John"
        parts = full_name.split(",")
        if len(parts) >= 2:
            return parts[1].strip()
        return full_name.strip()
    except Exception:
        return username


def write_service_account_report(service_df: pd.DataFrame) -> None:
    """
    Writes service accounts to a dated Excel report.
    Adds a 'Remediation Status' column pre-filled as 'Pending'
    and a 'Cherwell Ticket #' column left blank for manual entry.
    """
    if service_df.empty:
        logger.info("No service accounts to write to report.")
        return

    report_df = service_df.copy()
    report_df = report_df.fillna("")
    report_df["Cherwell Ticket #"]   = ""
    report_df["Ticket Pending Stage"] = ""
    report_df["Responsible Team"]     = ""
    report_df["Remediation Status"]   = "Pending"
    report_df["DBA Notes"]            = ""

    output_path = Path(OUTPUT_REPORT_PATH)
    report_df.to_excel(output_path, index=False)
    logger.info(f"Service account report written to: {output_path}")
    print(f"\n  Service account report saved to:\n  {output_path}")
