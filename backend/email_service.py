"""Transactional email via Gmail SMTP (App Password) or Google Workspace SMTP relay.

Reads SMTP_USER and SMTP_PASSWORD from the environment.
If either is unset, all send calls are silently skipped — no crash, no noise.
Swap to relay later: set SMTP_HOST=smtp-relay.gmail.com and leave SMTP_PASSWORD blank.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
_PORT = int(os.getenv("SMTP_PORT", "587"))
_USER = os.getenv("SMTP_USER", "")
_PASS = os.getenv("SMTP_PASSWORD", "")
_FROM = os.getenv("SMTP_FROM", _USER)  # defaults to SMTP_USER if not overridden

_ENABLED = bool(_USER)

_BASE_STYLE = """
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f5f5; margin: 0; padding: 32px 16px; }
  .card { background: #fff; border-radius: 10px; max-width: 520px;
          margin: 0 auto; padding: 36px 40px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
  .logo { font-size: 22px; font-weight: 700; color: #1a1a2e; margin-bottom: 24px; }
  .logo span { color: #4f46e5; }
  h2 { font-size: 20px; color: #1a1a2e; margin: 0 0 12px; }
  p { color: #444; line-height: 1.6; margin: 0 0 16px; font-size: 15px; }
  .btn { display: inline-block; background: #4f46e5; color: #fff !important;
         text-decoration: none; padding: 12px 28px; border-radius: 7px;
         font-weight: 600; font-size: 15px; margin: 8px 0 24px; }
  .footer { font-size: 12px; color: #999; margin-top: 24px; border-top: 1px solid #eee;
            padding-top: 16px; }
"""

CONWO_URL = os.getenv("CONWO_URL", "https://conwo.moveinsync.com")


def _send(to: str, subject: str, html: str) -> None:
    if not _ENABLED:
        logger.debug("Email disabled (SMTP_USER not set) — skipping send to %s", to)
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = _FROM
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(_HOST, _PORT, timeout=10) as s:
            s.starttls()
            if _PASS:
                s.login(_USER, _PASS)
            s.sendmail(_FROM, [to], msg.as_string())
        logger.info("Email sent to %s — %s", to, subject)
    except Exception:
        logger.exception("Failed to send email to %s — %s", to, subject)


def send_account_approved(to: str) -> None:
    """Notify a user that their Conwo account has been approved."""
    first = to.split("@")[0].split(".")[0].capitalize()
    html = f"""<!DOCTYPE html><html><head><style>{_BASE_STYLE}</style></head><body>
    <div class="card">
      <div class="logo">Con<span>wo</span></div>
      <h2>You're in, {first}! 🎉</h2>
      <p>Your Conwo account has been approved. You can now sign in and start
      asking questions about WorkInSync — products, configs, Jira history, and more.</p>
      <a class="btn" href="{CONWO_URL}/ask">Open Conwo →</a>
      <p>If you have any questions, reply to this email or ping the team on Slack.</p>
      <div class="footer">
        You're receiving this because an admin approved your Conwo account.<br>
        Conwo · MoveInSync · <a href="{CONWO_URL}">{CONWO_URL}</a>
      </div>
    </div>
    </body></html>"""
    _send(to, "Your Conwo access has been approved", html)


def send_agent_access_approved(to: str, agent_name: str, agent_id: str) -> None:
    """Notify a user that their request to access a specific agent was approved."""
    first = to.split("@")[0].split(".")[0].capitalize()
    agent_url = f"{CONWO_URL}/ask?agent={agent_id}"
    html = f"""<!DOCTYPE html><html><head><style>{_BASE_STYLE}</style></head><body>
    <div class="card">
      <div class="logo">Con<span>wo</span></div>
      <h2>Access granted: {agent_name}</h2>
      <p>Hi {first}, your request to access the <strong>{agent_name}</strong> agent
      on Conwo has been approved.</p>
      <a class="btn" href="{agent_url}">Open {agent_name} →</a>
      <p>Switch agents from the sidebar on the left after signing in.</p>
      <div class="footer">
        You're receiving this because an admin approved your agent access request.<br>
        Conwo · MoveInSync · <a href="{CONWO_URL}">{CONWO_URL}</a>
      </div>
    </div>
    </body></html>"""
    _send(to, f"Access granted: {agent_name} on Conwo", html)


def send_agent_access_rejected(to: str, agent_name: str) -> None:
    """Notify a user that their agent access request was rejected."""
    first = to.split("@")[0].split(".")[0].capitalize()
    html = f"""<!DOCTYPE html><html><head><style>{_BASE_STYLE}</style></head><body>
    <div class="card">
      <div class="logo">Con<span>wo</span></div>
      <h2>Access request update: {agent_name}</h2>
      <p>Hi {first}, your request to access the <strong>{agent_name}</strong> agent
      on Conwo was not approved at this time.</p>
      <p>If you think this is a mistake, reach out to your team admin or reply to this email.</p>
      <div class="footer">
        Conwo · MoveInSync · <a href="{CONWO_URL}">{CONWO_URL}</a>
      </div>
    </div>
    </body></html>"""
    _send(to, f"Access request update: {agent_name} on Conwo", html)
