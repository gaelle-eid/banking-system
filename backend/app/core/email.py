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


def send_verification_email(to: str, full_name: str, token: str, frontend_url: str):
    verify_link = f"{frontend_url}/verify-email?token={token}"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
      <h2>Welcome to Banking System, {full_name}!</h2>
      <p>Please verify your email address to activate your account.</p>
      <p>
        <a href="{verify_link}"
           style="background:#1F8A70;color:white;padding:10px 20px;
                  border-radius:8px;text-decoration:none;display:inline-block;">
          Verify my email
        </a>
      </p>
      <p style="color:#8A93A6;font-size:12px;">If you didn't create this account, you can ignore this email.</p>
    </div>
    """
    return send_email(to, "Verify your email - Banking System", html)


def send_welcome_email(to: str, full_name: str):
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
      <h2>Welcome aboard, {full_name}!</h2>
      <p>Your email has been verified and your account is now fully active.</p>
      <p>You can now log in, create accounts, and start banking.</p>
    </div>
    """
    return send_email(to, "Welcome to Banking System", html)



def send_transaction_email(to: str, full_name: str, tx_type: str, amount: str, account_label: str, new_balance: str):
    verb = {
        "deposit": "deposited into",
        "withdrawal": "withdrawn from",
        "transfer_debit": "sent from",
        "transfer_credit": "received into",
    }.get(tx_type, "processed on")

    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
      <h2>Transaction notification</h2>
      <p>Hi {full_name},</p>
      <p><strong>{amount}</strong> was {verb} your <strong>{account_label}</strong> account.</p>
      <p>New balance: <strong>{new_balance}</strong></p>
      <p style="color:#8A93A6;font-size:12px;">If you didn't expect this, contact support immediately.</p>
    </div>
    """
    return send_email(to, f"Transaction alert: {tx_type.replace('_', ' ').title()}", html)