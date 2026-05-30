# Story E9.S05: Auth Integration

**Feature:** [Frontend Self Report](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Интеграция авторизации: гостевой доступ (демо) для анонимных пользователей и полный доступ для авторизованных. Это позволяет показать продукт без регистрации.

## Что сделать

1. **Гостевой доступ**:
   - Анонимный пользователь видит демо-отчёт
   - Ограничения: только топ-1 тип, без evidence trail
   - CTA: "Зарегистрируйтесь для полного отчёта"
   - Данные хранятся в localStorage (не на backend)

2. **Авторизованный доступ**:
   - Полный отчёт: топ-3, Model A breakdown, evidence trail
   - Сохранение в историю (список профилей)
   - PDF export (опционально)

3. **Auth flow**:
   - Login/Register через модальное окно
   - После регистрации → merge localStorage данных с backend
   - JWT token в httpOnly cookie

4. **Protected routes**:
   - `/report/[profileId]` — доступен всем (гостевой=демо, авторизованный=полный)
   - `/history` — только для авторизованных
   - `/settings` — только для авторизованных

5. **UI компоненты**:
   - `AuthModal` — модальное окно login/register
   - `GuestBanner` — баннер "Вы используете демо-версию"
   - `UpgradeCTA` — кнопка "Получить полный отчёт"

## Затрагиваемые файлы

- `frontend/src/components/auth-modal.tsx` — новый
- `frontend/src/components/guest-banner.tsx` — новый
- `frontend/src/components/upgrade-cta.tsx` — новый
- `frontend/src/lib/auth.ts` — обновить
- `frontend/src/middleware.ts` — обновить (protected routes)

## Критерии приёмки

- [ ] Гость видит демо-отчёт с ограничениями
- [ ] Авторизованный видит полный отчёт
- [ ] Auth modal работает (login/register)
- [ ] localStorage merge при регистрации
- [ ] Protected routes работают
- [ ] ruff, mypy, eslint — 0 ошибок

## Примечания

- Demo mode: данные не сохраняются на backend
- Merge: при регистрации → POST /profiles с данными из localStorage
- JWT в httpOnly cookie для безопасности
