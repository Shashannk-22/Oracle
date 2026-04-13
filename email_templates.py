# =============================================================================
# email_templates.py
# All HTML email bodies live here. Logic stays in automate_email.py.
# To update wording or styling, only edit this file.
# =============================================================================

from config import DEADLINE_DATE, SENDER_EMAIL


def user_notification_email(first_name: str, account_table_html: str) -> tuple[str, str]:
    """
    Returns (subject, html_body) for the user notification email.
    Sent to each human user account found in the fallout report.
    """
    subject = "ACTION REQUIRED — Unauthorized Access Remediation"

    body = f"""
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">

<p>Hello {first_name},</p>

<p>
PJM Policy states that all access to PJM systems must be authorized.
You are being contacted because your Oracle database account has been identified
in our quarterly fallout report as <strong>undocumented or lacking valid authorization</strong>.
</p>

<p>Please review the account details below and complete the appropriate remediation
action by <strong><span style="background-color: #FFFF00;">{DEADLINE_DATE}</span></strong>.</p>

<hr>

<p><strong>Your Account Details:</strong></p>
{account_table_html}

<hr>

<p><strong>Remediation Actions:</strong></p>
<ol>
  <li>
    <strong>Access IS still needed</strong> — Submit an authorization request via
    <a href="https://accessmanager.pjm.com">Access Manager</a>.
    <br>
    &nbsp;&nbsp;&nbsp;a. If assistance is needed, please contact the Access Management Team
    (<a href="mailto:access_management_team@pjm.com">access_management_team@pjm.com</a>).
  </li>
  <li>
    <strong>Access is NOT needed</strong> — Reply to this email and the DBA Team
    will facilitate access removal.
  </li>
</ol>

<p>
If no response is received by
<strong><span style="background-color: #FFFF00;">{DEADLINE_DATE}</span></strong>,
access will be removed automatically.
</p>

<p>Thank you,</p>

<p>
Varsha John<br>
Sr. DBA, Data Solutions<br>
<br>
C: (610) 585-4797 | <a href="mailto:{SENDER_EMAIL}">{SENDER_EMAIL}</a><br>
PJM Interconnection | 2750 Monroe Blvd. | Audubon, PA 19403
</p>

</body>
</html>
"""
    return subject, body


def service_account_summary_email(service_table_html: str, total_count: int) -> tuple[str, str]:
    """
    Returns (subject, html_body) for the internal DBA service account summary email.
    Sent once per run to the DBA team — not to individual users.
    """
    from datetime import date
    run_date = date.today().strftime("%B %d, %Y")

    subject = f"[DBA ACTION REQUIRED] Service Account Fallout Report — {run_date}"

    body = f"""
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">

<p>Hello DBA Team,</p>

<p>
This is an automated summary of the <strong>{total_count} service account(s)</strong>
identified in this quarter's fallout report that require manual follow-up.
</p>

<p>
For each account below, please:
</p>
<ol>
  <li>Check for an associated <strong>Cherwell / ServiceNow ticket</strong>.</li>
  <li>If a ticket exists — review its pending stage and update the tracker with status and responsible team.</li>
  <li>If no ticket exists — open a new Cherwell ticket and follow up with the blocking team.</li>
  <li>Once resolved — update the remediation tracker with final status.</li>
</ol>

<hr>

<p><strong>Service Accounts Requiring Action ({run_date}):</strong></p>
{service_table_html}

<hr>

<p>
This email was generated automatically by the Fallout Report Automation script.<br>
Please do not reply to this email. For questions, contact
<a href="mailto:{SENDER_EMAIL}">{SENDER_EMAIL}</a>.
</p>

<p>
Varsha John<br>
Sr. DBA, Data Solutions<br>
<br>
C: (610) 585-4797 | <a href="mailto:{SENDER_EMAIL}">{SENDER_EMAIL}</a><br>
PJM Interconnection | 2750 Monroe Blvd. | Audubon, PA 19403
</p>

</body>
</html>
"""
    return subject, body


def error_alert_email(error_message: str) -> tuple[str, str]:
    """
    Returns (subject, html_body) for a failure alert email.
    Sent to the DBA team if the script crashes mid-run.
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = "ALERT — Fallout Report Automation Failed"

    body = f"""
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">

<p>Hello DBA Team,</p>

<p>
The automated Fallout Report email process <strong>failed</strong> at
<strong>{timestamp}</strong> with the following error:
</p>

<pre style="background-color: #f5f5f5; padding: 12px; border-left: 4px solid #cc0000;">
{error_message}
</pre>

<p>
Please review the script, verify the spreadsheet is in the correct format,
and re-run manually if needed.
</p>

<p>
Fallout Report Automation System<br>
PJM Interconnection
</p>

</body>
</html>
"""
    return subject, body
