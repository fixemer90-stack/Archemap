# Story E2.03: Email верификация

**Feature:** [Authentication & Identity](Archemap/docs/features/v1/E2-identity/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Подтверждение email через одноразовый токен.

## Что сделать

1. EmailVerification model
2. VerificationService: create, verify, resend
3. Email sending через SMTP/Console
4. Anti-enumeration

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/modules/auth/verification.py` | Создан — VerificationService |
| `app/modules/auth/models.py` | Создан — EmailVerification model |
| `app/infrastructure/email.py` | Создан — SMTP provider |

## Критерии приёмки

- [x] Токен генерируется при регистрации
- [x] Email отправляется
- [x] Подтверждение по токену
- [x] Anti-enumeration на resend

## Примечания

Часть Epic 2: Identity.
