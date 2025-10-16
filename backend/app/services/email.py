import smtplib
from email.message import EmailMessage
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from ..core.config import settings


# Setup Jinja2 environment for email templates
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def send_email(
    to_email: str,
    subject: str,
    body: str = None,
    template: str = None,
    context: dict = None
) -> None:
    """
    Send an email with either plain text body or HTML template.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text body (optional, for backward compatibility)
        template: Template name (e.g., "email/welcome.html")
        context: Template context variables
    """
    host = getattr(settings, "smtp_host", None) or "localhost"
    port = int(getattr(settings, "smtp_port", 1025))

    msg = EmailMessage()
    msg["From"] = "noreply@regami.local"
    msg["To"] = to_email
    msg["Subject"] = subject

    # Use template if provided, otherwise use plain text body
    if template and context is not None:
        context["subject"] = subject
        context.setdefault("app_url", "https://regami.com")
        html_content = jinja_env.get_template(template).render(context)
        msg.set_content("Please view this email in an HTML-capable email client.")
        msg.add_alternative(html_content, subtype="html")
    else:
        msg.set_content(body or "")

    try:
        with smtplib.SMTP(host, port, timeout=3) as s:
            s.send_message(msg)
    except Exception:
        # In tests or local dev without SMTP, silently ignore.
        return
