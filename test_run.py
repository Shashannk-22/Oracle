# =============================================================================
# test_run.py  —  TEST MODE: prints emails to screen, sends nothing
#
# HOW TO RUN:
#   Option A: drop your .xlsx into this folder, then:
#       python test_run.py
#   Option B: pass the path directly:
#       python test_run.py "C:\path\to\FalloutReport.xlsx"
#
# WHAT TO CHECK:
#   [ ] Correct file detected (shown at top)
#   [ ] Each email looks right — name, table, deadline
#   [ ] Deadline = today + 60 days
#   [ ] Service_Account_Report_*.xlsx created in the same folder
#   [ ] run_log.csv has entries for this run
#
# When happy: python automate_email.py
# =============================================================================

import sys
import re
import logging
from datetime import date

import dotenv
dotenv.load_dotenv(dotenv.find_dotenv())

from config import (
    FILE_PATH, SENDER_EMAIL, DBA_TEAM_EMAIL,
    USER_EMAIL_DOMAIN, DEADLINE_DATE, COL_USERNAME,
)
from report_handler import (
    load_and_validate, split_accounts,
    get_user_dataframe, get_first_name,
    write_service_account_report,
)
from email_templates import (
    user_notification_email,
    service_account_summary_email,
)
from run_logger import write_log

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test_run.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FAKE send_email — same signature as pjmlib, prints instead of sending
# ---------------------------------------------------------------------------
def send_email(send_to, subject, body, send_from):
    divider = "─" * 66
    print(f"\n  ┌{divider}┐")
    print(f"  │  TEST MODE — NOT SENT")
    print(f"  │  FROM    : {send_from}")
    print(f"  │  TO      : {send_to}")
    print(f"  │  SUBJECT : {subject}")
    print(f"  ├{divider}┤")
    plain = re.sub(r"<[^>]+>", "", body)
    plain = re.sub(r"&nbsp;", " ", plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
    for line in plain.splitlines():
        print(f"  │  {line}")
    print(f"  └{divider}┘\n")


# ---------------------------------------------------------------------------
# Process user accounts
# ---------------------------------------------------------------------------
def process_user_accounts(user_df) -> dict:
    summary = {"sent": 0, "failed": 0, "skipped": 0}
    usernames = user_df[COL_USERNAME].dropna().unique().tolist()
    logger.info(f"  Found {len(usernames)} unique user account(s)")

    for username in usernames:
        email_address = f"{username}@{USER_EMAIL_DOMAIN}"
        try:
            person_df  = get_user_dataframe(user_df, username)
            first_name = get_first_name(user_df, username)

            if person_df.empty:
                logger.warning(f"  SKIP — no rows for: {username}")
                write_log("EMAIL_SKIPPED", username=username,
                          email_sent_to=email_address, status="SKIPPED",
                          notes="No data rows found")
                summary["skipped"] += 1
                continue

            table_html    = person_df.to_html(index=False, border=1)
            subject, body = user_notification_email(first_name, table_html)
            send_email(send_to=email_address, subject=subject,
                       body=body, send_from=SENDER_EMAIL)

            write_log("EMAIL_SENT", username=username,
                      email_sent_to=email_address, status="TEST_MODE",
                      notes=f"Deadline: {DEADLINE_DATE}")
            summary["sent"] += 1

        except Exception as e:
            logger.error(f"  ERROR for {username}: {e}")
            write_log("EMAIL_FAILED", username=username,
                      email_sent_to=email_address, status="FAILED", notes=str(e))
            summary["failed"] += 1

    return summary


# ---------------------------------------------------------------------------
# Process service accounts
# ---------------------------------------------------------------------------
def process_service_accounts(service_df) -> None:
    if service_df.empty:
        logger.info("  No service accounts found — skipping")
        return

    total = len(service_df)

    try:
        write_service_account_report(service_df)
        logger.info(f"  Excel report written — {total} service account(s)")
        write_log("SERVICE_REPORT_WRITTEN", status="TEST_MODE",
                  notes=f"{total} service accounts")
    except Exception as e:
        logger.error(f"  Failed to write report: {e}")
        write_log("SERVICE_REPORT_WRITTEN", status="FAILED", notes=str(e))

    try:
        table_html    = service_df.fillna("").to_html(index=False, border=1)
        subject, body = service_account_summary_email(table_html, total)
        send_email(send_to=DBA_TEAM_EMAIL, subject=subject,
                   body=body, send_from=SENDER_EMAIL)
        write_log("SERVICE_EMAIL_SENT", email_sent_to=DBA_TEAM_EMAIL,
                  status="TEST_MODE", notes=f"{total} service accounts")
    except Exception as e:
        logger.error(f"  Failed to build service email: {e}")
        write_log("SERVICE_EMAIL_FAILED", email_sent_to=DBA_TEAM_EMAIL,
                  status="FAILED", notes=str(e))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def test_run():
    bar = "=" * 68
    run_date = date.today().strftime("%Y-%m-%d")

    print(f"\n{bar}")
    print(f"  FALLOUT REPORT AUTOMATION — TEST MODE")
    print(f"  Date : {run_date}")
    print(f"{bar}")

    # Guard: no file found
    if not FILE_PATH:
        print("")
        print("  ERROR: No Excel fallout report found.")
        print("")
        print("  Fix — do one of these:")
        print("  1. Copy your .xlsx file into this folder:")
        print(f"     C:\\Users\\ramiss\\Desktop\\Fallback Report Automation\\")
        print("")
        print("  2. Pass the path directly:")
        print('     python test_run.py "C:\\path\\to\\FalloutReport.xlsx"')
        print(f"\n{bar}\n")
        sys.exit(1)

    print(f"  File : {FILE_PATH}")
    print(f"  No emails will be sent — all output printed below")
    print(f"{bar}\n")

    try:
        df                  = load_and_validate()
        user_df, service_df = split_accounts(df)

        print("\n--- USER ACCOUNTS " + "-" * 50)
        user_summary = process_user_accounts(user_df)

        print("\n--- SERVICE ACCOUNTS " + "-" * 47)
        process_service_accounts(service_df)

        print(f"\n{bar}")
        print(f"  TEST RUN COMPLETE")
        print(f"{bar}")
        print(f"  File           : {FILE_PATH}")
        print(f"  User emails    : {user_summary['sent']} printed  "
              f"| {user_summary['failed']} failed  "
              f"| {user_summary['skipped']} skipped")
        print(f"  Service accts  : {len(service_df)}")
        print(f"\n  Checklist before going live:")
        print(f"  [ ] Email content looks correct — name, table, deadline")
        print(f"  [ ] Deadline shown is {DEADLINE_DATE}  (today + 60 days)")
        print(f"  [ ] Service_Account_Report_*.xlsx created in your folder")
        print(f"  [ ] run_log.csv has entries for this run")
        print(f"\n  When ready:  python automate_email.py")
        print(f"{bar}\n")

        write_log("RUN_COMPLETE", status="TEST_MODE",
                  notes=(f"Sent:{user_summary['sent']} "
                         f"Failed:{user_summary['failed']} "
                         f"Skipped:{user_summary['skipped']} "
                         f"Service:{len(service_df)}"))

    except Exception as e:
        logger.critical(f"Test run failed: {e}", exc_info=True)
        print(f"\n  ERROR: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    test_run()
