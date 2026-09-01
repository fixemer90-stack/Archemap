"""Email HTML templates."""


def verify_email_template(link: str) -> tuple[str, str]:
    """Returns (html_body, text_body) for verification email."""
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
     max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
  <h2 style="margin: 0 0 16px;">Подтвердите email</h2>
  <p style="margin: 0 0 24px; color: #666;">
    Спасибо за регистрацию в Astrotype. Нажмите кнопку ниже, чтобы подтвердить ваш email.
  </p>
  <a href="{link}"
     style="display: inline-block; background: #000; color: #fff; padding: 12px 24px;
            border-radius: 6px; text-decoration: none; font-weight: 500;">
    Подтвердить email
  </a>
  <p style="margin: 24px 0 0; color: #999; font-size: 13px;">
    Ссылка действует 24 часа. Если вы не регистрировались, просто проигнорируйте это письмо.
  </p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0 16px;">
  <p style="color: #999; font-size: 12px;">Astrotype — астрологический анализ личности</p>
</body>
</html>
"""
    text = f"""Подтвердите email

Спасибо за регистрацию в Astrotype. Перейдите по ссылке для подтверждения:

{link}

Ссылка действует 24 часа. Если вы не регистрировались, проигнорируйте это письмо.

--
Astrotype
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
  <h2 style="margin: 0 0 16px;">Новая ссылка для подтверждения</h2>
  <p style="margin: 0 0 24px; color: #666;">
    Вот новая ссылка для подтверждения вашего email в Astrotype.
  </p>
  <a href="{link}"
     style="display: inline-block; background: #000; color: #fff; padding: 12px 24px;
            border-radius: 6px; text-decoration: none; font-weight: 500;">
    Подтвердить email
  </a>
  <p style="margin: 24px 0 0; color: #999; font-size: 13px;">
    Ссылка действует 24 часа.
  </p>
</body>
</html>
"""
    text = f"""Новая ссылка для подтверждения

Вот новая ссылка для подтверждения email в Astrotype:

{link}

Ссылка действует 24 часа.

--
Astrotype
"""
    return html.strip(), text.strip()


def password_reset_template(link: str) -> tuple[str, str]:
    """Returns (html_body, text_body) for password-reset email."""
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
     max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
  <h2 style="margin: 0 0 16px;">Сброс пароля</h2>
  <p style="margin: 0 0 24px; color: #666;">
    Вы запросили сброс пароля для Astrotype. Нажмите кнопку ниже.
  </p>
  <a href="{link}"
     style="display: inline-block; background: #000; color: #fff; padding: 12px 24px;
            border-radius: 6px; text-decoration: none; font-weight: 500;">
    Сбросить пароль
  </a>
  <p style="margin: 24px 0 0; color: #999; font-size: 13px;">
    Ссылка действует 1 час. Если вы не запрашивали сброс, проигнорируйте это письмо.
  </p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0 16px;">
  <p style="color: #999; font-size: 12px;">Astrotype — астрологический анализ личности</p>
</body>
</html>
"""
    text = f"""Сброс пароля

Вы запросили сброс пароля для Astrotype. Перейдите по ссылке:

{link}

Ссылка действует 1 час. Если вы не запрашивали сброс, проигнорируйте это письмо.

--
Astrotype
"""
    return html.strip(), text.strip()
