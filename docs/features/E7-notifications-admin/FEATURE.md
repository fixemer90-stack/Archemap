# Feature E7: Notifications & Admin

## Цель

Уведомления (email, SMS, push), напоминания о продлении, admin dashboard, content editor, аналитика, audit trail.

## Зависимости

`E5`, `E6`

## Критерии приёмки

- [ ] Email: transactional (отчёт готов, подписка)
- [ ] SMS: подтверждение, важные события
- [ ] Push: web и mobile (FCM/APNs)
- [ ] Напоминания: за 7/3/1 день до окончания подписки
- [ ] Admin: поиск пользователя, подписки, ручная активация
- [ ] Content Editor: редактирование правил и шаблонов
- [ ] Analytics: PostHog, события signup/login/payment/report
- [ ] Audit trail: лог действий, доступен в admin

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Email-уведомления: SMTP/SendPulse, шаблоны на RU/EN, transactional events](S01-email-notifications.md) | ⬜ Не начато |
| S02 | [SMS: SMS.ru / Infobip, rate-limit 3/день/user](S02-sms-notifications.md) | ⬜ Не начато |
| S03 | [Push: FCM/APNs, web push, device registration, push при готовности отчёта](S03-push-notifications.md) | ⬜ Не начато |
| S04 | [Напоминания: cron за 7/3/1 день, email + push](S04-renewal-reminders.md) | ⬜ Не начато |
| S05 | [Admin dashboard: поиск пользователя, просмотр подписок, ручная активация/отмена](S05-admin-dashboard.md) | ⬜ Не начато |
| S06 | [Content Editor: WYSIWYG для шаблонов, JSON editor для правил, preview](S06-content-editor.md) | ⬜ Не начато |
| S07 | [Analytics (PostHog): signup, login, report_generated, payment_success, dashboard](S07-analytics.md) | ⬜ Не начато |
| S08 | [Audit trail: лог изменений подписки/профиля, доступен в admin](S08-audit-trail.md) | ⬜ Не начато |
