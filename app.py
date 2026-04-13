# =============================================================================
# app.py
# Flask web server — serves the UI and runs the fallout report automation.
#
# Run:  python app.py
# Then open:  http://localhost:5000
# =============================================================================

import os
import sys
import re
import json
import logging
import traceback
from pathlib import Path
from datetime import date, timedelta
from flask import Flask, render_template_string, request, Response, jsonify
import pandas as pd

# Suppress Flask's default logger noise
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)
UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Settings (mirrors config.py)
# ---------------------------------------------------------------------------
SENDER_EMAIL      = "varsha.john@pjm.com"
DBA_TEAM_EMAIL    = "varsha.john@pjm.com"
USER_EMAIL_DOMAIN = "pjm.com"
DEADLINE_DAYS     = 60
DEADLINE_DATE     = (date.today() + timedelta(days=DEADLINE_DAYS)).strftime("%B %d, %Y")

COL_ACCOUNT_TYPE  = "tbAccountTypeData"
COL_USERNAME      = "tbActualLoginNameData"
COL_FULLNAME      = "tbFullnameData"
COL_ENVIRONMENT   = "tbEnvironmentData"
COL_TARGET        = "tbTargetData"
USER_ACCOUNT_VALUE    = "User Account"
SERVICE_ACCOUNT_VALUE = "Service Account"
REQUIRED_COLUMNS  = [COL_ACCOUNT_TYPE, COL_USERNAME, COL_FULLNAME, COL_ENVIRONMENT]


# ---------------------------------------------------------------------------
# HTML UI — single file, no templates folder needed
# ---------------------------------------------------------------------------
UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fallout Report Automation</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #0f1117;
    --surface:  #181c27;
    --border:   #2a2f3d;
    --accent:   #4f8ef7;
    --accent2:  #38c98a;
    --warn:     #f0a500;
    --danger:   #e05252;
    --text:     #d4d8e8;
    --muted:    #6b7280;
    --mono:     'IBM Plex Mono', monospace;
    --sans:     'IBM Plex Sans', sans-serif;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    font-size: 14px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── Header ── */
  header {
    border-bottom: 1px solid var(--border);
    padding: 18px 32px;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .logo {
    width: 32px; height: 32px;
    background: var(--accent);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--mono); font-weight: 500; font-size: 13px;
    color: #fff; flex-shrink: 0;
  }
  header h1 { font-size: 15px; font-weight: 600; letter-spacing: .01em; }
  header span { font-size: 12px; color: var(--muted); margin-left: 4px; }

  /* ── Layout ── */
  main {
    flex: 1;
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 0;
    height: calc(100vh - 61px);
  }

  /* ── Left panel ── */
  .panel-left {
    border-right: 1px solid var(--border);
    padding: 28px 24px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    overflow-y: auto;
  }

  .section-label {
    font-size: 11px;
    font-weight: 500;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 10px;
  }

  /* ── Drop zone ── */
  .dropzone {
    border: 1.5px dashed var(--border);
    border-radius: 10px;
    padding: 32px 20px;
    text-align: center;
    cursor: pointer;
    transition: border-color .2s, background .2s;
    position: relative;
  }
  .dropzone:hover, .dropzone.drag-over {
    border-color: var(--accent);
    background: rgba(79,142,247,.06);
  }
  .dropzone input[type=file] {
    position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }
  .dropzone-icon {
    width: 40px; height: 40px;
    border: 1.5px solid var(--border);
    border-radius: 8px;
    margin: 0 auto 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  .dropzone p { font-size: 13px; color: var(--muted); line-height: 1.6; }
  .dropzone strong { color: var(--text); font-weight: 500; }
  .file-chosen {
    margin-top: 10px;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--accent2);
    word-break: break-all;
  }

  /* ── Mode toggle ── */
  .mode-row {
    display: flex;
    background: #12151f;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 4px;
    gap: 4px;
  }
  .mode-btn {
    flex: 1; padding: 8px 10px;
    border: none; border-radius: 6px;
    font-family: var(--sans); font-size: 13px; font-weight: 500;
    cursor: pointer; transition: all .15s;
    background: transparent; color: var(--muted);
  }
  .mode-btn.active {
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 1px 3px rgba(0,0,0,.4);
  }
  .mode-btn.live.active { color: var(--warn); }

  /* ── Info cards ── */
  .info-grid { display: flex; flex-direction: column; gap: 8px; }
  .info-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .info-card .label { font-size: 12px; color: var(--muted); }
  .info-card .value { font-family: var(--mono); font-size: 12px; color: var(--text); text-align: right; }
  .info-card .value.accent  { color: var(--accent); }
  .info-card .value.accent2 { color: var(--accent2); }
  .info-card .value.warn    { color: var(--warn); }

  /* ── Run button ── */
  .run-btn {
    width: 100%;
    padding: 13px;
    background: var(--accent);
    border: none; border-radius: 8px;
    color: #fff;
    font-family: var(--sans); font-size: 14px; font-weight: 600;
    cursor: pointer; transition: opacity .15s, transform .1s;
    letter-spacing: .02em;
  }
  .run-btn:hover:not(:disabled) { opacity: .9; }
  .run-btn:active:not(:disabled) { transform: scale(.99); }
  .run-btn:disabled { opacity: .4; cursor: not-allowed; }
  .run-btn.live { background: var(--warn); color: #000; }

  /* ── Right panel ── */
  .panel-right {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── Tabs ── */
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    flex-shrink: 0;
  }
  .tab {
    padding: 14px 16px 12px;
    font-size: 13px; font-weight: 500;
    color: var(--muted);
    cursor: pointer; border: none; background: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: color .15s, border-color .15s;
  }
  .tab.active { color: var(--text); border-bottom-color: var(--accent); }
  .tab-badge {
    display: inline-block;
    background: var(--border);
    color: var(--muted);
    font-size: 10px; font-weight: 600;
    padding: 1px 6px; border-radius: 10px;
    margin-left: 6px;
  }
  .tab.active .tab-badge { background: var(--accent); color: #fff; }

  /* ── Tab content ── */
  .tab-content { display: none; flex: 1; overflow-y: auto; padding: 24px; }
  .tab-content.active { display: flex; flex-direction: column; gap: 16px; }

  /* ── Log terminal ── */
  .terminal {
    background: #090b10;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.8;
    min-height: 200px;
    max-height: 500px;
    overflow-y: auto;
    flex: 1;
  }
  .terminal .line-info   { color: #6b9ef7; }
  .terminal .line-ok     { color: var(--accent2); }
  .terminal .line-warn   { color: var(--warn); }
  .terminal .line-error  { color: var(--danger); }
  .terminal .line-dim    { color: var(--muted); }
  .terminal .line-head   { color: #fff; font-weight: 500; }
  .terminal .cursor {
    display: inline-block; width: 8px; height: 13px;
    background: var(--accent); vertical-align: middle;
    animation: blink .9s step-end infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }

  /* ── Email preview cards ── */
  .email-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  .email-card-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    display: flex; gap: 12px; align-items: flex-start;
    flex-wrap: wrap;
  }
  .email-badge {
    font-size: 10px; font-weight: 600; letter-spacing: .06em;
    text-transform: uppercase; padding: 3px 8px; border-radius: 4px;
    flex-shrink: 0;
  }
  .badge-user    { background: rgba(79,142,247,.15); color: var(--accent); }
  .badge-service { background: rgba(240,165,0,.12);  color: var(--warn);   }
  .badge-error   { background: rgba(224,82,82,.12);  color: var(--danger); }
  .email-meta { flex: 1; display: flex; flex-direction: column; gap: 2px; }
  .email-meta .to   { font-size: 12px; color: var(--muted); }
  .email-meta .subj { font-size: 13px; font-weight: 500; color: var(--text); }
  .email-body {
    padding: 14px 16px;
    font-size: 12px; line-height: 1.7; color: var(--muted);
    white-space: pre-wrap; font-family: var(--mono);
    max-height: 280px; overflow-y: auto;
  }

  /* ── Summary cards ── */
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    text-align: center;
  }
  .stat-card .num {
    font-family: var(--mono); font-size: 28px; font-weight: 500;
    line-height: 1;
    margin-bottom: 6px;
  }
  .stat-card .lbl { font-size: 11px; color: var(--muted); letter-spacing: .04em; }
  .stat-card.ok   .num { color: var(--accent2); }
  .stat-card.fail .num { color: var(--danger);  }
  .stat-card.skip .num { color: var(--muted);   }
  .stat-card.svc  .num { color: var(--warn);    }

  /* ── Empty state ── */
  .empty {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: var(--muted); gap: 10px; padding: 60px;
    text-align: center;
  }
  .empty-icon { font-size: 36px; opacity: .3; }
  .empty p { font-size: 13px; line-height: 1.6; max-width: 280px; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>

<header>
  <div class="logo">DB</div>
  <div>
    <h1>Fallout Report Automation <span>Oracle Access Remediation</span></h1>
  </div>
</header>

<main>
  <!-- ── LEFT PANEL ── -->
  <div class="panel-left">

    <div>
      <div class="section-label">Report File</div>
      <div class="dropzone" id="dropzone">
        <input type="file" id="fileInput" accept=".xlsx,.xls">
        <div class="dropzone-icon">📊</div>
        <p><strong>Drop your fallout report here</strong><br>or click to browse</p>
        <div class="file-chosen" id="fileChosen"></div>
      </div>
    </div>

    <div>
      <div class="section-label">Run Mode</div>
      <div class="mode-row">
        <button class="mode-btn active" id="btnTest" onclick="setMode('test')">
          Test — preview only
        </button>
        <button class="mode-btn live" id="btnLive" onclick="setMode('live')">
          Live — send emails
        </button>
      </div>
      <p style="font-size:11px;color:var(--muted);margin-top:8px;line-height:1.6">
        Test mode prints all emails to screen. No emails are sent.
      </p>
    </div>

    <div>
      <div class="section-label">Configuration</div>
      <div class="info-grid">
        <div class="info-card">
          <span class="label">Sender</span>
          <span class="value accent">varsha.john@pjm.com</span>
        </div>
        <div class="info-card">
          <span class="label">Deadline</span>
          <span class="value warn">{{ deadline }}</span>
        </div>
        <div class="info-card">
          <span class="label">Email domain</span>
          <span class="value">@pjm.com</span>
        </div>
        <div class="info-card">
          <span class="label">DBA summary to</span>
          <span class="value">varsha.john@pjm.com</span>
        </div>
      </div>
    </div>

    <button class="run-btn" id="runBtn" disabled onclick="runAutomation()">
      Select a file to begin
    </button>

  </div>

  <!-- ── RIGHT PANEL ── -->
  <div class="panel-right">

    <div class="tabs">
      <button class="tab active" onclick="switchTab('log')">
        Live Log <span class="tab-badge" id="badge-log">—</span>
      </button>
      <button class="tab" onclick="switchTab('emails')">
        Email Previews <span class="tab-badge" id="badge-emails">0</span>
      </button>
      <button class="tab" onclick="switchTab('summary')">
        Summary <span class="tab-badge" id="badge-summary">—</span>
      </button>
    </div>

    <!-- Log tab -->
    <div class="tab-content active" id="tab-log">
      <div class="terminal" id="terminal">
        <span class="line-dim">Waiting for file upload...</span>
      </div>
    </div>

    <!-- Emails tab -->
    <div class="tab-content" id="tab-emails">
      <div class="empty" id="emails-empty">
        <div class="empty-icon">✉</div>
        <p>Email previews will appear here once you run the automation.</p>
      </div>
      <div id="emails-list"></div>
    </div>

    <!-- Summary tab -->
    <div class="tab-content" id="tab-summary">
      <div class="empty" id="summary-empty">
        <div class="empty-icon">📋</div>
        <p>Run the automation to see the summary.</p>
      </div>
      <div id="summary-content" style="display:none">
        <div class="summary-grid">
          <div class="stat-card ok">
            <div class="num" id="stat-sent">0</div>
            <div class="lbl">Emails sent</div>
          </div>
          <div class="stat-card fail">
            <div class="num" id="stat-failed">0</div>
            <div class="lbl">Failed</div>
          </div>
          <div class="stat-card skip">
            <div class="num" id="stat-skipped">0</div>
            <div class="lbl">Skipped</div>
          </div>
          <div class="stat-card svc">
            <div class="num" id="stat-service">0</div>
            <div class="lbl">Service accts</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</main>

<script>
let mode = 'test';
let emailCount = 0;

// ── Mode toggle ──
function setMode(m) {
  mode = m;
  document.getElementById('btnTest').classList.toggle('active', m === 'test');
  document.getElementById('btnLive').classList.toggle('active', m === 'live');
  const btn = document.getElementById('runBtn');
  if (document.getElementById('fileInput').files.length > 0) {
    btn.classList.toggle('live', m === 'live');
    btn.textContent = m === 'test'
      ? 'Run test — preview emails'
      : 'Send live emails';
  }
}

// ── File input ──
const fileInput = document.getElementById('fileInput');
const dropzone  = document.getElementById('dropzone');

fileInput.addEventListener('change', () => {
  const f = fileInput.files[0];
  if (!f) return;
  document.getElementById('fileChosen').textContent = f.name;
  const btn = document.getElementById('runBtn');
  btn.disabled = false;
  btn.textContent = mode === 'test' ? 'Run test — preview emails' : 'Send live emails';
  btn.classList.toggle('live', mode === 'live');
  log(`<span class="line-ok">✓ File selected: ${f.name}</span>`);
});

dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('drag-over');
  const dt = new DataTransfer();
  dt.items.add(e.dataTransfer.files[0]);
  fileInput.files = dt.files;
  fileInput.dispatchEvent(new Event('change'));
});

// ── Tab switching ──
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t, i) => {
    t.classList.toggle('active', ['log','emails','summary'][i] === name);
  });
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
}

// ── Terminal log ──
const terminal = document.getElementById('terminal');
let firstLog = true;
function log(html) {
  if (firstLog) { terminal.innerHTML = ''; firstLog = false; }
  const div = document.createElement('div');
  div.innerHTML = html;
  terminal.appendChild(div);
  terminal.scrollTop = terminal.scrollHeight;
}
function logLine(text) {
  const cls = text.includes('ERROR') || text.includes('FAIL') ? 'line-error'
            : text.includes('SENT') || text.includes('✓') || text.includes('OK') ? 'line-ok'
            : text.includes('SKIP') || text.includes('WARN') ? 'line-warn'
            : text.includes('===') || text.includes('---') ? 'line-head'
            : 'line-dim';
  log(`<span class="${cls}">${escHtml(text)}</span>`);
}
function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Add email preview card ──
function addEmailCard(data) {
  document.getElementById('emails-empty').style.display = 'none';
  emailCount++;
  document.getElementById('badge-emails').textContent = emailCount;

  const type = data.type === 'service' ? 'service' : 'user';
  const badgeClass = type === 'service' ? 'badge-service' : 'badge-user';
  const badgeLabel = type === 'service' ? 'Service — DBA summary' : 'User notification';

  const card = document.createElement('div');
  card.className = 'email-card';
  card.innerHTML = `
    <div class="email-card-header">
      <span class="email-badge ${badgeClass}">${badgeLabel}</span>
      <div class="email-meta">
        <div class="to">To: ${escHtml(data.to)}</div>
        <div class="subj">${escHtml(data.subject)}</div>
      </div>
    </div>
    <div class="email-body">${escHtml(data.body)}</div>
  `;
  document.getElementById('emails-list').appendChild(card);
}

// ── Show summary ──
function showSummary(data) {
  document.getElementById('summary-empty').style.display = 'none';
  document.getElementById('summary-content').style.display = 'block';
  document.getElementById('stat-sent').textContent    = data.sent;
  document.getElementById('stat-failed').textContent  = data.failed;
  document.getElementById('stat-skipped').textContent = data.skipped;
  document.getElementById('stat-service').textContent = data.service;
  document.getElementById('badge-summary').textContent = 'Done';
}

// ── Run automation ──
async function runAutomation() {
  const file = fileInput.files[0];
  if (!file) return;

  // Reset
  terminal.innerHTML = '';
  firstLog = false;
  emailCount = 0;
  document.getElementById('badge-emails').textContent = '0';
  document.getElementById('badge-summary').textContent = '—';
  document.getElementById('emails-empty').style.display = 'flex';
  document.getElementById('emails-list').innerHTML = '';
  document.getElementById('summary-empty').style.display = 'flex';
  document.getElementById('summary-content').style.display = 'none';

  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  btn.textContent = 'Running…';

  switchTab('log');

  const formData = new FormData();
  formData.append('file', file);
  formData.append('mode', mode);

  try {
    const resp = await fetch('/run', { method: 'POST', body: formData });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        if (!part.startsWith('data:')) continue;
        try {
          const payload = JSON.parse(part.slice(5).trim());
          if (payload.type === 'log')     logLine(payload.text);
          if (payload.type === 'email')   addEmailCard(payload);
          if (payload.type === 'summary') showSummary(payload);
        } catch {}
      }
    }
  } catch (err) {
    log(`<span class="line-error">Connection error: ${escHtml(String(err))}</span>`);
  }

  btn.disabled = false;
  btn.textContent = mode === 'test' ? 'Run test — preview emails' : 'Send live emails';
  log(`<span class="line-dim">─── run finished ───</span><span class="cursor"></span>`);
}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_first_name(user_df: pd.DataFrame, username: str) -> str:
    try:
        full = user_df[user_df[COL_USERNAME] == username].iloc[0][COL_FULLNAME]
        if pd.isna(full) or not isinstance(full, str):
            return username
        parts = full.split(",")
        return parts[1].strip() if len(parts) >= 2 else full.strip()
    except Exception:
        return username


def build_user_email_body(first_name: str, table_html: str) -> tuple:
    subject = "ACTION REQUIRED — Unauthorized Access Remediation"
    body = f"""
<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#333">
<p>Hello {first_name},</p>
<p>PJM Policy states that all access to PJM systems must be authorized.
Your Oracle database account has been identified in the quarterly fallout report
as <strong>undocumented or lacking valid authorization</strong>.</p>
<p>Please complete the appropriate remediation action by
<strong><span style="background:#FFFF00">{DEADLINE_DATE}</span></strong>.</p>
<hr>
<p><strong>Your Account Details:</strong></p>
{table_html}
<hr>
<p><strong>Remediation Actions:</strong></p>
<ol>
  <li><strong>Access IS needed</strong> — Submit an authorization request via Access Manager.</li>
  <li><strong>Access NOT needed</strong> — Reply to this email and DBA Team will remove access.</li>
</ol>
<p>If no response by <strong><span style="background:#FFFF00">{DEADLINE_DATE}</span></strong>,
access will be removed automatically.</p>
<p>Thank you,<br>Varsha John<br>Sr. DBA, Data Solutions<br>
C: (610) 585-4797 | {SENDER_EMAIL}<br>
PJM Interconnection | 2750 Monroe Blvd. | Audubon, PA 19403</p>
</body></html>"""
    return subject, body


def build_service_email_body(table_html: str, total: int) -> tuple:
    run_date = date.today().strftime("%B %d, %Y")
    subject  = f"[DBA ACTION REQUIRED] Service Account Fallout Report — {run_date}"
    body = f"""
<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#333">
<p>Hello DBA Team,</p>
<p>Automated summary of <strong>{total} service account(s)</strong> requiring manual follow-up.</p>
<ol>
  <li>Check for an associated Cherwell / ServiceNow ticket.</li>
  <li>If ticket exists — review pending stage and update tracker.</li>
  <li>If no ticket — open a new Cherwell ticket and follow up.</li>
  <li>Once resolved — update remediation tracker with final status.</li>
</ol>
<hr>
<p><strong>Service Accounts ({run_date}):</strong></p>
{table_html}
<hr>
<p>Varsha John | Sr. DBA, Data Solutions | {SENDER_EMAIL}</p>
</body></html>"""
    return subject, body


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template_string(UI_HTML, deadline=DEADLINE_DATE)


@app.route("/run", methods=["POST"])
def run():
    """Handles file upload and streams SSE events back to the browser."""
    uploaded = request.files.get("file")
    mode     = request.form.get("mode", "test")

    # Save file and load data BEFORE the generator starts
    # Flask closes the file handle once the response starts streaming
    if not uploaded:
        def _no_file():
            yield sse({"type": "log", "text": "ERROR: No file received."})
        return Response(_no_file(), mimetype="text/event-stream",
                        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    save_path = UPLOAD_FOLDER / uploaded.filename
    uploaded.save(str(save_path))
    filename = uploaded.filename

    try:
        df = pd.read_excel(save_path)
    except Exception as e:
        def _bad_file(err=e):
            yield sse({"type": "log", "text": f"ERROR reading file: {err}"})
        return Response(_bad_file(), mimetype="text/event-stream",
                        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    def stream():
        yield sse({"type": "log", "text": f"File received: {filename}"})
        yield sse({"type": "log", "text": f"Loaded {len(df)} rows from spreadsheet"})
        

        # ── Validate columns ──
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            yield sse({"type": "log", "text": f"ERROR: Missing columns: {missing}"})
            yield sse({"type": "log", "text": f"Found columns: {list(df.columns)}"})
            return

        # ── Drop blank account types ──
        before = len(df)
        df = df[df[COL_ACCOUNT_TYPE].notna()]
        if len(df) < before:
            yield sse({"type": "log", "text": f"WARN: Dropped {before - len(df)} rows with blank account type"})

        # ── Split ──
        user_df    = df[df[COL_ACCOUNT_TYPE] == USER_ACCOUNT_VALUE].copy()
        service_df = df[df[COL_ACCOUNT_TYPE] == SERVICE_ACCOUNT_VALUE].copy()
        yield sse({"type": "log", "text": f"User accounts:    {len(user_df)}"})
        yield sse({"type": "log", "text": f"Service accounts: {len(service_df)}"})
        yield sse({"type": "log", "text": "─" * 48})

        summary = {"sent": 0, "failed": 0, "skipped": 0, "service": len(service_df)}

        # ── User accounts ──
        yield sse({"type": "log", "text": "--- USER ACCOUNTS ---"})
        usernames = user_df[COL_USERNAME].dropna().unique().tolist()
        yield sse({"type": "log", "text": f"Found {len(usernames)} unique user(s)"})

        for username in usernames:
            email_addr = f"{username}@{USER_EMAIL_DOMAIN}"
            try:
                cols      = [c for c in [COL_ENVIRONMENT, COL_TARGET, COL_USERNAME] if c in user_df.columns]
                person_df = user_df[user_df[COL_USERNAME] == username].reset_index(drop=True)[cols]

                if person_df.empty:
                    yield sse({"type": "log", "text": f"SKIP: no rows for {username}"})
                    summary["skipped"] += 1
                    continue

                first_name  = get_first_name(user_df, username)
                table_html  = person_df.to_html(index=False, border=1)
                subject, body = build_user_email_body(first_name, table_html)

                if mode == "live":
                    # Import and use real pjmlib
                    from pjmlib.emailutils import send_email
                    send_email(send_to=email_addr, subject=subject,
                               body=body, send_from=SENDER_EMAIL)
                    yield sse({"type": "log", "text": f"SENT → {email_addr}"})
                else:
                    yield sse({"type": "log", "text": f"TEST → {email_addr}"})

                # Stream email preview to UI
                yield sse({
                    "type":    "email",
                    "email_type": "user",
                    "to":      email_addr,
                    "subject": subject,
                    "body":    strip_html(body),
                })
                summary["sent"] += 1

            except Exception as e:
                yield sse({"type": "log", "text": f"ERROR {username}: {e}"})
                summary["failed"] += 1

        # ── Service accounts ──
        yield sse({"type": "log", "text": "─" * 48})
        yield sse({"type": "log", "text": "--- SERVICE ACCOUNTS ---"})

        if service_df.empty:
            yield sse({"type": "log", "text": "No service accounts — skipping"})
        else:
            total = len(service_df)

            # Write Excel report
            try:
                report_df = service_df.fillna("").copy()
                report_df["Cherwell Ticket #"]    = ""
                report_df["Ticket Pending Stage"] = ""
                report_df["Responsible Team"]     = ""
                report_df["Remediation Status"]   = "Pending"
                report_df["DBA Notes"]            = ""
                out_name = f"Service_Account_Report_{date.today().strftime('%Y%m%d')}.xlsx"
                out_path = save_path.parent / out_name
                report_df.to_excel(str(out_path), index=False)
                yield sse({"type": "log", "text": f"✓ Service report written: {out_name}"})
            except Exception as e:
                yield sse({"type": "log", "text": f"ERROR writing report: {e}"})

            # Service account email
            table_html    = service_df.fillna("").to_html(index=False, border=1)
            subject, body = build_service_email_body(table_html, total)

            if mode == "live":
                try:
                    from pjmlib.emailutils import send_email
                    send_email(send_to=DBA_TEAM_EMAIL, subject=subject,
                               body=body, send_from=SENDER_EMAIL)
                    yield sse({"type": "log", "text": f"SENT DBA summary → {DBA_TEAM_EMAIL}"})
                except Exception as e:
                    yield sse({"type": "log", "text": f"ERROR sending DBA email: {e}"})
            else:
                yield sse({"type": "log", "text": f"TEST DBA summary → {DBA_TEAM_EMAIL}"})

            yield sse({
                "type":    "email",
                "email_type": "service",
                "to":      DBA_TEAM_EMAIL,
                "subject": subject,
                "body":    strip_html(body),
            })

        # ── Done ──
        yield sse({"type": "log", "text": "─" * 48})
        yield sse({"type": "log",
                   "text": f"RUN COMPLETE — Sent:{summary['sent']} "
                           f"Failed:{summary['failed']} "
                           f"Skipped:{summary['skipped']} "
                           f"Service:{summary['service']}"})
        yield sse({"type": "summary", **summary})

    return Response(stream(), mimetype="text/event-stream",
                    headers={"X-Accel-Buffering": "no",
                             "Cache-Control": "no-cache"})


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 52)
    print("  Fallout Report Automation — Web UI")
    print("  Open in your browser: http://localhost:5000")
    print("=" * 52 + "\n")
    app.run(debug=False, port=5000)
