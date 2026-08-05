import resend
from app.core.config import settings

resend.api_key = settings.resend_api_key

FROM_ADDRESS = "Banking System <onboarding@resend.dev>"


def send_email(to: str, subject: str, html: str) -> dict:
    """Send an email via Resend. Returns the API response dict."""
    return resend.Emails.send({
        "from": FROM_ADDRESS,
        "to": [to],
        "subject": subject,
        "html": html,
    })