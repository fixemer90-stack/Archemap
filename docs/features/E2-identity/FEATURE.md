# Feature E2: Authentication & Identity

## Цель

Пользователь может зарегистрироваться, войти, подтвердить email, выйти, восстановить пароль и войти через OAuth-провайдера. Безопасность: JWT, rate limiting, token blacklist.

## Зависимости

`E1`

## Критерии приёмки

- [ ] Регистрация по email+password с хешированием (Argon2id/bcrypt)
- [ ] JWT access + refresh токены
- [ ] Email верификация через одноразовый токен
- [ ] Logout через blacklist токенов
- [ ] Yandex OAuth 2.0 + PKCE
- [ ] VK ID OAuth 2.0 + PKCE
- [ ] Привязка OAuth к существующему аккаунту
- [ ] Сброс пароля по email
- [ ] Rate limiting: 5 попыток / 15 мин на login
- [ ] Cookie-first browser session: login/refresh/logout через HttpOnly cookies, frontend не хранит JWT
- [x] Hotfix: stale Authorization header не затеняет валидную cookie-backed session

## Документы

- Workflow: [WORKFLOW.md](WORKFLOW.md)
- API contract: [API.md](API.md)
- SRS: [SRS-E2-identity-auth.md](../../SRS/SRS-E2-identity-auth.md)

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [User model + регистрация по email/password: модели User, EmailVerification, хеширование паролей, endpoint POST /auth/register](S01-user-model-registration.md) | ✅ Готово |
| S02 | [JWT access/refresh токены: создание, валидация, decode, refresh flow](S02-jwt-tokens.md) | ✅ Готово |
| S03 | [Email верификация: генерация токена, отправка email, подтверждение, anti-enumeration](S03-email-verification.md) | ✅ Готово |
| S04 | [Token blacklist (logout): Redis-based blacklist, POST /auth/logout, проверка при валидации](S04-token-blacklist-logout.md) | ✅ Готово |
| S05 | [Yandex ID OAuth: Authorization Code flow, exchange code, get user info, account linking по email](S05-yandex-oauth.md) | ✅ Готово |
| S06 | [VK ID OAuth: аналогично Yandex, VK-specific endpoints/scopes](S06-vk-oauth.md) | ⬜ Не начато |
| S07 | [Привязка OAuth-провайдеров: link/unlink из настроек, IdentityLink model](S07-account-linking.md) | 🟡 В процессе |
| S08 | [Сброс пароля: запрос по email, токен 24ч, новый пароль, anti-enumeration](S08-password-reset.md) | ✅ Готово |
| S09 | [Rate limiting входа: Redis INCR+EXPIRE, 5 попыток/15 мин, HTTP 429](S09-rate-limiting.md) | ✅ Готово |
| S10 | [Cookie-first session auth cleanup: HttpOnly cookies для browser flow, stale Bearer fallback, refresh/logout/session bootstrap, report-page 401 resilience](S10-cookie-first-session-auth.md) | 🟡 В процессе |
