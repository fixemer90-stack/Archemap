"""Email HTML templates."""


def verify_email_template(link: str) -> tuple[str, str]:
    """Returns (html_body, text_body) for verification email."""
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
     max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
  <h2 style="margin: 0 0 16px;">Verify your email</h2>
  <p style="margin: 0 0 24px; color: #666;">
    Thanks for signing up for Archemap. Click the button below to verify your email address.
  </p>
  <a href="{link}"
     style="display: inline-block; background: #000; color: #fff; padding: 12px 24px;
            border-radius: 6px; text-decoration: none; font-weight: 500;">
    Verify email
  </a>
  <p style="margin: 24px 0 0; color: #999; font-size: 13px;">
    This link expires in 24 hours. If you didn't create an account, you can ignore this email.
  </p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0 16px;">
  <p style="color: #999; font-size: 12px;">Archemap — Subscription management</p>
</body>
</html>
"""
    text = f"""Verify your email

Thanks for signing up for Archemap. Click the link below to verify your email address:

{link}

This link expires in 24 hours. If you didn't create an account, you can ignore this email.
"""
    return html.strip(), text.strip()


def resend_verification_template(link: str) -> tuple[str, str]:
    """Returns (html_body, text_body) for resend verification email."""
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
     max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
  <h2 style="margin: 0 0 16px;">Verify your email</h2>
  <p style="margin: 0 0 24px; color: #666;">
    Here's a new verification link for your Archemap account.
  </p>
  <a href="{link}"
     style="display: inline-block; background: #000; color: #fff; padding: 12px 24px;
            border-radius: 6px; text-decoration: none; font-weight: 500;">
    Verify email
  </a>
  <p style="margin: 24px 0 0; color: #999; font-size: 13px;">
    This link expires in 24 hours.
  </p>
</body>
</html>
"""
    text = f"""Verify your email

Here's a new verification link for your Archemap account:

{link}

This link expires in 24 hours.
"""
    return html.strip(), text.strip()
