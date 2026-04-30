import json
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from jinja2 import Template
except ImportError:
    print("[email] ERROR: jinja2 not installed. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_FILE = os.path.join(REPO_ROOT, "config.json")
CLASSIFIED_FILE = os.path.join(REPO_ROOT, "classified_items.json")

IST = timezone(timedelta(hours=5, minutes=30))
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# ---------------------------------------------------------------------------
# HTML email template (Jinja2)
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Digest</title>
</head>
<body style="margin:0;padding:0;background-color:#edf2f7;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#edf2f7;padding:24px 0;">
<tr><td align="center">
<table width="660" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <!-- HEADER -->
  <tr>
    <td style="background-color:#1a1a2e;padding:28px 32px;">
      <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.3px;">Daily AI Digest</h1>
      <p style="margin:6px 0 0;color:#a0aec0;font-size:13px;">
        {{ date }}&nbsp;&nbsp;|&nbsp;&nbsp;Role:&nbsp;<strong style="color:#e2e8f0;">{{ role }}</strong>
      </p>
    </td>
  </tr>

  <!-- CAUTION BANNER -->
  <tr>
    <td style="padding:14px 32px;background-color:#fffbeb;border-left:4px solid #f59e0b;">
      <p style="margin:0;font-size:12px;color:#78350f;line-height:1.5;">
        <strong>CAUTION:</strong>&nbsp; This is an automated digest. Verify critical information before acting on it.
      </p>
    </td>
  </tr>

  {% if deep_reads %}
  <!-- DEEP READ SECTION HEADER -->
  <tr>
    <td style="padding:28px 32px 12px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="background-color:#1a1a2e;border-radius:6px;padding:11px 18px;">
            <span style="color:#ffffff;font-size:15px;font-weight:700;">DEEP READ</span>
            <span style="color:#718096;font-size:12px;margin-left:10px;">{{ deep_reads|length }} article{% if deep_reads|length != 1 %}s{% endif %} &mdash; prioritise these</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  {% for item in deep_reads %}
  <tr>
    <td style="padding:0 32px {% if loop.last %}8px{% else %}0{% endif %};">
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;margin-bottom:10px;">
        <tr>
          <td style="padding:16px 20px;">
            <p style="margin:0 0 2px;font-size:10px;color:#a0aec0;text-transform:uppercase;letter-spacing:1px;">{{ item.source }}</p>
            <h2 style="margin:0 0 10px;font-size:15px;line-height:1.45;font-weight:600;">
              <a href="{{ item.url }}" style="color:#2b6cb0;text-decoration:none;">{{ item.title }}</a>
            </h2>
            <p style="margin:0 0 10px;font-size:13px;color:#4a5568;line-height:1.65;">{{ item.summary }}</p>
            <p style="margin:0;font-size:12px;color:#718096;font-style:italic;border-left:3px solid #e2e8f0;padding-left:10px;">{{ item.reason }}</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  {% endfor %}
  {% endif %}

  {% if skims %}
  <!-- SKIM SECTION HEADER -->
  <tr>
    <td style="padding:20px 32px 12px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="background-color:#2d3748;border-radius:6px;padding:11px 18px;">
            <span style="color:#ffffff;font-size:15px;font-weight:700;">SKIM</span>
            <span style="color:#718096;font-size:12px;margin-left:10px;">{{ skims|length }} headline{% if skims|length != 1 %}s{% endif %}</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;">
        {% for item in skims %}
        <tr style="background-color:{% if loop.index is odd %}#f7fafc{% else %}#ffffff{% endif %};">
          <td style="padding:10px 16px;{% if not loop.last %}border-bottom:1px solid #edf2f7;{% endif %}">
            <a href="{{ item.url }}" style="color:#2b6cb0;text-decoration:none;font-size:13px;line-height:1.5;">{{ item.title }}</a>
            <span style="color:#a0aec0;font-size:11px;margin-left:6px;">&mdash;&nbsp;{{ item.source }}</span>
          </td>
        </tr>
        {% endfor %}
      </table>
    </td>
  </tr>
  {% endif %}

  {% if not deep_reads and not skims %}
  <tr>
    <td style="padding:48px 32px;text-align:center;">
      <p style="color:#a0aec0;font-size:14px;margin:0;">No relevant AI news found today. Check back tomorrow.</p>
    </td>
  </tr>
  {% endif %}

  <!-- FOOTER -->
  <tr>
    <td style="padding:20px 32px;text-align:center;border-top:1px solid #edf2f7;background-color:#f7fafc;">
      <p style="margin:0;font-size:11px;color:#a0aec0;">
        Generated by <strong>Daily AI Digest</strong> | GitHub Actions
      </p>
      <p style="margin:4px 0 0;font-size:10px;color:#cbd5e0;">{{ date }} &nbsp;&middot;&nbsp; Role: {{ role }}</p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        print(f"[email] ERROR: {CONFIG_FILE} not found. Run setup.py first.", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_classified() -> list[dict]:
    if not os.path.exists(CLASSIFIED_FILE):
        print(f"[email] ERROR: {CLASSIFIED_FILE} not found. Run classify.py first.", file=sys.stderr)
        sys.exit(1)
    with open(CLASSIFIED_FILE, encoding="utf-8") as f:
        return json.load(f)


def render_html(role: str, date_str: str, deep_reads: list[dict], skims: list[dict]) -> str:
    return Template(HTML_TEMPLATE).render(
        role=role,
        date=date_str,
        deep_reads=deep_reads,
        skims=skims,
    )


def send_via_smtp(subject: str, html_body: str, sender: str, password: str, recipient: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, [recipient], msg.as_string())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config = load_config()
    items = load_classified()

    role = config.get("role", "Software Developer")
    sender = os.environ.get("GMAIL_USER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    recipient = config.get("recipient_email", "").strip()

    if not sender:
        print("[email] ERROR: GMAIL_USER environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not password:
        print("[email] ERROR: GMAIL_APP_PASSWORD environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not recipient:
        print("[email] ERROR: recipient_email not set in config.json.", file=sys.stderr)
        sys.exit(1)

    date_str = datetime.now(IST).strftime("%A, %d %B %Y")
    subject = f"AI Digest – {date_str} | {role}"

    deep_reads = [i for i in items if i.get("category") == "deep-read"]
    skims = [i for i in items if i.get("category") == "skim"]
    print(f"[email] Building digest — deep-read: {len(deep_reads)}, skim: {len(skims)}")

    html_body = render_html(role, date_str, deep_reads, skims)

    print(f"[email] Sending to {recipient} via {SMTP_HOST}:{SMTP_PORT}...")
    send_via_smtp(subject, html_body, sender, password, recipient)
    print(f"[email] Sent: {subject}")


if __name__ == "__main__":
    main()
