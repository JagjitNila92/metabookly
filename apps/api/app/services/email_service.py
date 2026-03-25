"""
Transactional email service using AWS SES v2.

All sends are best-effort — failures are logged but never raise to the caller.
In SES sandbox mode both sender and recipient must be verified identities.
"""
import asyncio
import logging
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


# ── HTML template helpers ──────────────────────────────────────────────────────

def _wrap_html(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden;">
          <!-- Header -->
          <tr>
            <td style="background:#f59e0b;padding:24px 32px;">
              <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;">Metabookly</h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              {body}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:#f8fafc;padding:20px 32px;border-top:1px solid #e2e8f0;">
              <p style="margin:0;color:#94a3b8;font-size:12px;">
                This is an automated message from Metabookly. Please do not reply to this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _field_row(label: str, value: str) -> str:
    return f"""
    <tr>
      <td style="padding:6px 0;color:#64748b;font-size:14px;width:160px;vertical-align:top;">{label}</td>
      <td style="padding:6px 0;color:#0f172a;font-size:14px;font-weight:500;">{value}</td>
    </tr>"""


# ── SES send (synchronous — called via asyncio.to_thread) ────────────────────

def _send_ses_email(to_address: str, subject: str, html_body: str) -> None:
    settings = get_settings()
    client = boto3.client("sesv2", region_name=settings.aws_region)
    client.send_email(
        FromEmailAddress=settings.ses_from_email,
        Destination={"ToAddresses": [to_address]},
        Content={
            "Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            }
        },
    )


async def _send(to_address: str, subject: str, html_body: str) -> None:
    """Send an email. Logs and swallows all errors — never raises."""
    try:
        await asyncio.to_thread(_send_ses_email, to_address, subject, html_body)
        logger.info("Email sent to %s: %s", to_address, subject)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "MessageRejected" and "not verified" in str(e):
            logger.warning(
                "SES sandbox: %s is not a verified identity — email not sent. "
                "Verify the address in SES or request production access.",
                to_address,
            )
        else:
            logger.warning("SES send failed to %s: %s", to_address, e)
    except Exception as exc:
        logger.warning("Email send error to %s: %s", to_address, exc)


# ── Email 1: Notify distributor of new account link request ───────────────────

async def notify_distributor_new_request(
    *,
    distributor_email: str,
    distributor_name: str,
    retailer_company: str,
    retailer_email: str,
    account_number: str | None,
    request_id: str,
) -> None:
    """
    Sent to the distributor when a retailer submits an account link request.
    """
    account_row = _field_row("Account number", account_number or "Not provided")

    body = f"""
    <h2 style="margin:0 0 8px;color:#0f172a;font-size:22px;">New Account Link Request</h2>
    <p style="margin:0 0 24px;color:#64748b;font-size:15px;">
      A retailer has requested to link their trade account with <strong>{distributor_name}</strong>.
      Please review and approve or reject the request.
    </p>

    <table cellpadding="0" cellspacing="0" style="width:100%;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin-bottom:24px;">
      <tr><td colspan="2" style="padding-bottom:12px;">
        <p style="margin:0;font-size:13px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">Retailer Details</p>
      </td></tr>
      {_field_row("Company name", retailer_company)}
      {_field_row("Email address", retailer_email)}
      {account_row}
      {_field_row("Request ID", request_id)}
    </table>

    <a href="https://metabookly.com/distributor/requests"
       style="display:inline-block;background:#f59e0b;color:#ffffff;text-decoration:none;
              padding:12px 24px;border-radius:8px;font-size:15px;font-weight:600;">
      Review Request
    </a>

    <p style="margin:24px 0 0;color:#94a3b8;font-size:13px;">
      You can approve or reject this request from the Metabookly distributor portal.
    </p>"""

    await _send(
        to_address=distributor_email,
        subject=f"New account link request from {retailer_company} — {distributor_name}",
        html_body=_wrap_html("New Account Link Request", body),
    )


# ── Email 2: Notify retailer of approve/reject decision ───────────────────────

async def notify_retailer_request_approved(
    *,
    retailer_email: str,
    retailer_company: str,
    distributor_name: str,
    account_number: str | None,
) -> None:
    """Sent to the retailer when their account link request is approved."""
    body = f"""
    <h2 style="margin:0 0 8px;color:#0f172a;font-size:22px;">Account Link Approved</h2>
    <p style="margin:0 0 24px;color:#64748b;font-size:15px;">
      Great news, <strong>{retailer_company}</strong>! Your request to link your trade account
      with <strong>{distributor_name}</strong> has been approved.
    </p>

    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:20px;margin-bottom:24px;">
      <p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#166534;">✓ Account linked successfully</p>
      <p style="margin:0;font-size:14px;color:#16a34a;">
        You can now see live trade pricing from {distributor_name} in the catalogue.
        {'Account number: <strong>' + account_number + '</strong>' if account_number else ''}
      </p>
    </div>

    <a href="https://metabookly.com/catalog"
       style="display:inline-block;background:#f59e0b;color:#ffffff;text-decoration:none;
              padding:12px 24px;border-radius:8px;font-size:15px;font-weight:600;">
      Browse the Catalogue
    </a>

    <p style="margin:24px 0 0;color:#94a3b8;font-size:13px;">
      Manage your linked accounts from your
      <a href="https://metabookly.com/account" style="color:#f59e0b;">My Account</a> page.
    </p>"""

    await _send(
        to_address=retailer_email,
        subject=f"Your {distributor_name} account has been linked — Metabookly",
        html_body=_wrap_html("Account Link Approved", body),
    )


async def notify_retailer_request_rejected(
    *,
    retailer_email: str,
    retailer_company: str,
    distributor_name: str,
    account_number: str | None,
    rejection_reason: str | None,
) -> None:
    """Sent to the retailer when their account link request is rejected."""
    reason_block = ""
    if rejection_reason:
        reason_block = f"""
    <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:16px;margin:16px 0;">
      <p style="margin:0 0 4px;font-size:13px;font-weight:600;color:#9a3412;">Reason provided:</p>
      <p style="margin:0;font-size:14px;color:#c2410c;">{rejection_reason}</p>
    </div>"""

    account_line = f"<p style='margin:4px 0 0;font-size:13px;color:#94a3b8;'>Account number submitted: {account_number}</p>" if account_number else ""

    body = f"""
    <h2 style="margin:0 0 8px;color:#0f172a;font-size:22px;">Account Link Request Declined</h2>
    <p style="margin:0 0 24px;color:#64748b;font-size:15px;">
      Unfortunately, your request to link your trade account with
      <strong>{distributor_name}</strong> has not been approved at this time.
    </p>

    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:20px;margin-bottom:8px;">
      <p style="margin:0;font-size:15px;font-weight:600;color:#991b1b;">✗ Request declined — {distributor_name}</p>
      {account_line}
    </div>

    {reason_block}

    <p style="margin:24px 0 16px;color:#475569;font-size:14px;">
      If you believe this is an error or would like to resubmit with updated details,
      you can withdraw this request and try again from your account page.
    </p>

    <a href="https://metabookly.com/account"
       style="display:inline-block;background:#f59e0b;color:#ffffff;text-decoration:none;
              padding:12px 24px;border-radius:8px;font-size:15px;font-weight:600;">
      Go to My Account
    </a>"""

    await _send(
        to_address=retailer_email,
        subject=f"Your {distributor_name} account link request was not approved — Metabookly",
        html_body=_wrap_html("Account Link Request Declined", body),
    )
