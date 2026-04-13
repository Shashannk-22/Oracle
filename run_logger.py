# =============================================================================
# run_logger.py
# Writes a CSV audit log of every email sent, every skip, and every error.
# One row per event. Appends on each run — never overwrites history.
# =============================================================================

import csv
import logging
from datetime import datetime
from pathlib import Path
from config import LOG_FILE_PATH

logger = logging.getLogger(__name__)

LOG_HEADERS = ["timestamp", "run_date", "event_type", "username", "email_sent_to", "status", "notes"]


def _ensure_log_exists():
    """Creates the log file with headers if it doesn't exist yet."""
    log_path = Path(LOG_FILE_PATH)
    if not log_path.exists():
        with open(log_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_HEADERS)
            writer.writeheader()
        logger.info(f"Created new log file at: {LOG_FILE_PATH}")


def write_log(event_type: str, username: str = "", email_sent_to: str = "",
              status: str = "", notes: str = ""):
    """
    Appends one row to the run log CSV.

    event_type options: EMAIL_SENT, EMAIL_FAILED, SERVICE_REPORT_WRITTEN,
                        SERVICE_EMAIL_SENT, SERVICE_EMAIL_FAILED,
                        SCRIPT_ERROR, RUN_COMPLETE
    """
    _ensure_log_exists()
    row = {
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "run_date":     datetime.now().strftime("%Y-%m-%d"),
        "event_type":   event_type,
        "username":     username,
        "email_sent_to": email_sent_to,
        "status":       status,
        "notes":        notes,
    }
    try:
        with open(LOG_FILE_PATH, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_HEADERS)
            writer.writerow(row)
    except Exception as e:
        logger.error(f"Failed to write to run log: {e}")
