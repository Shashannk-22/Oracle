# =============================================================================
# automate_email.py  —  PRODUCTION: sends real emails via pjmlib
#
# HOW TO RUN:
#   Option A: drop your .xlsx into this folder, then:
#       python automate_email.py
#   Option B: pass the path directly:
#       python automate_email.py "C:\path\to\FalloutReport.xlsx"
# =============================================================================

import logging
import sys
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
    error_alert_email,
)
from run_logger import write_log
from pjmlib.emailutils import send_email

# ---------------------------------------------------------------------------
# Logging — prints to console AND writes to fallout_automation.log
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("fallout_automation.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Process user accounts — sends one email per unique username
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

            logger.info(f"  SENT → {email_address}  (deadline: {DEADLINE_DATE})")
            write_log("EMAIL_SENT", username=username,
                      email_sent_to=email_address, status="SUCCESS",
                      notes=f"Deadline: {DEADLINE_DATE}")
            summary["sent"] += 1

        except Exception as e:
            logger.error(f"  FAILED → {email_address} — {e}")
            write_log("EMAIL_FAILED", username=username,
                      email_sent_to=email_address, status="FAILED", notes=str(e))
            summary["failed"] += 1

    return summary


# ---------------------------------------------------------------------------
# Process service accounts — writes Excel report + sends DBA summary email
# ---------------------------------------------------------------------------
def process_service_accounts(service_df) -> None:
    if service_df.empty:
        logger.info("  No service accounts found — skipping")
        return

    total = len(service_df)

    # Write Excel report
    try:
        write_service_account_report(service_df)
        write_log("SERVICE_REPORT_WRITTEN", status="SUCCESS",
                  notes=f"{total} service accounts written")
    except Exception as e:
        logger.error(f"  Failed to write service account report: {e}")
        write_log("SERVICE_REPORT_WRITTEN", status="FAILED", notes=str(e))

    # Send DBA summary email
    try:
        table_html    = service_df.fillna("").to_html(index=False, border=1)
        subject, body = service_account_summary_email(table_html, total)
        send_email(send_to=DBA_TEAM_EMAIL, subject=subject,
                   body=body, send_from=SENDER_EMAIL)
        logger.info(f"  Service account summary sent → {DBA_TEAM_EMAIL}")
        write_log("SERVICE_EMAIL_SENT", email_sent_to=DBA_TEAM_EMAIL,
                  status="SUCCESS", notes=f"{total} service accounts")
    except Exception as e:
        logger.error(f"  Failed to send service account email: {e}")
        write_log("SERVICE_EMAIL_FAILED", email_sent_to=DBA_TEAM_EMAIL,
                  status="FAILED", notes=str(e))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def automate_email():
    bar = "=" * 60
    run_date = date.today().strftime("%Y-%m-%d")

    logger.info(bar)
    logger.info(f"Fallout Report Automation — {run_date}")
    logger.info(bar)

    # Guard: no file found
    if not FILE_PATH:
        logger.critical("No Excel file found.")
        logger.critical(f"Copy your .xlsx into: {__file__}")
        logger.critical('Or run: python automate_email.py "C:\\path\\to\\file.xlsx"')
        sys.exit(1)

    logger.info(f"File: {FILE_PATH}")

    try:
        df                  = load_and_validate()
        user_df, service_df = split_accounts(df)

        logger.info("\n--- USER ACCOUNTS ---")
        user_summary = process_user_accounts(user_df)

        logger.info("\n--- SERVICE ACCOUNTS ---")
        process_service_accounts(service_df)

        logger.info(f"\n{bar}")
        logger.info("RUN COMPLETE")
        logger.info(f"  Emails sent    : {user_summary['sent']}")
        logger.info(f"  Emails failed  : {user_summary['failed']}")
        logger.info(f"  Emails skipped : {user_summary['skipped']}")
        logger.info(f"  Service accts  : {len(service_df)}")
        logger.info(bar)

        write_log("RUN_COMPLETE", status="SUCCESS",
                  notes=(f"Sent:{user_summary['sent']} "
                         f"Failed:{user_summary['failed']} "
                         f"Skipped:{user_summary['skipped']} "
                         f"Service:{len(service_df)}"))

    except Exception as e:
        logger.critical(f"Script failed: {e}", exc_info=True)
        write_log("SCRIPT_ERROR", status="FAILED", notes=str(e))
        try:
            subject, body = error_alert_email(str(e))
            send_email(send_to=DBA_TEAM_EMAIL, subject=subject,
                       body=body, send_from=SENDER_EMAIL)
            logger.info(f"Error alert sent to {DBA_TEAM_EMAIL}")
        except Exception as alert_err:
            logger.error(f"Could not send error alert: {alert_err}")
        sys.exit(1)


if __name__ == "__main__":
    automate_email()
