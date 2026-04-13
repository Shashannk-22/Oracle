# =============================================================================
# config.py
# =============================================================================

import os
import sys
from pathlib import Path
from datetime import date, timedelta

def _find_excel_file() -> str:
    # 1. Command-line argument
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.exists() and p.suffix.lower() in (".xlsx", ".xls"):
            return str(p)

    # 2. .env variable
    env_path = os.getenv("FILE_PATH", "")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return str(p)

    # 3. Scan scripts folder
    script_dir = Path(__file__).parent
    xlsx_files = sorted(
        [f for f in script_dir.glob("*.xlsx")
         if not f.name.startswith("Service_Account_Report")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if xlsx_files:
        return str(xlsx_files[0])

    # 4. Scan current working directory
    cwd_files = sorted(
        [f for f in Path.cwd().glob("*.xlsx")
         if not f.name.startswith("Service_Account_Report")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if cwd_files:
        return str(cwd_files[0])

    # Nothing found — return empty string, scripts will handle the error visibly
    return ""


# Run file detection — never crash silently
_detected = _find_excel_file()

if _detected:
    FILE_PATH = _detected
else:
    FILE_PATH = ""
    print("=" * 60)
    print("  ERROR: No Excel fallout report found.")
    print("")
    print("  Fix: Copy your .xlsx file into this folder:")
    print(f"  {Path(__file__).parent}")
    print("")
    print("  Or run with the file path:")
    print('  python test_run.py "C:\\path\\to\\FalloutReport.xlsx"')
    print("=" * 60)

# Output paths
OUTPUT_REPORT_PATH = str(
    Path(FILE_PATH).parent / f"Service_Account_Report_{date.today().strftime('%Y%m%d')}.xlsx"
) if FILE_PATH else ""

LOG_FILE_PATH = str(Path(__file__).parent / "run_log.csv")

# ---------------------------------------------------------------------------
# EMAIL SETTINGS
# ---------------------------------------------------------------------------
SENDER_EMAIL      = "varsha.john@pjm.com"
DBA_TEAM_EMAIL    = "varsha.john@pjm.com"
USER_EMAIL_DOMAIN = "pjm.com"

# ---------------------------------------------------------------------------
# DEADLINE
# ---------------------------------------------------------------------------
DEADLINE_DAYS = 60
DEADLINE_DATE = (date.today() + timedelta(days=DEADLINE_DAYS)).strftime("%B %d, %Y")

# ---------------------------------------------------------------------------
# EXCEL COLUMN NAMES
# ---------------------------------------------------------------------------
COL_ACCOUNT_TYPE  = "tbAccountTypeData"
COL_USERNAME      = "tbActualLoginNameData"
COL_FULLNAME      = "tbFullnameData"
COL_ENVIRONMENT   = "tbEnvironmentData"
COL_TARGET        = "tbTargetData"

USER_ACCOUNT_VALUE    = "User Account"
SERVICE_ACCOUNT_VALUE = "Service Account"
