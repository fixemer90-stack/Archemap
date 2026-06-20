# Story E2.10: Cookie-first session auth cleanup

**Feature:** [Authentication & Identity](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

В frontend/backend auth flow исторически смешивались две модели:

1. JS-managed JWT:
   - `astrotype_token`;
   - `astrotype_refresh_token`;
   - frontend читал токены через `js-cookie` и отправлял `Authorization: Bearer ...`.

2. Cookie-backed JWT session:
   - `access_token`;
   - `refresh_token`;
   - OAuth/Yandex ставил HttpOnly cookies;
   - browser отправлял cookies через `credentials: "include"`.

Из-за этого появлялся auth-flap: frontend мог отправить протухший Bearer header, backend проверял его первым и возвращал `401`, хотя в cookies могла быть валидная сессия. На report page это проявлялось как поздний `401` на `/api/v1/reports?product=self&limit=100`, сброс состояния и пустой экран.

Предыдущий hotfix уже сделал backend устойчивее: `get_current_user` проверяет token candidates и не даёт stale Bearer header затенить валидную cookie-session. Эта story закрыла целевую архитектуру для browser app: cookie-first session model без JS-readable JWT как source of truth.

## Итог реализации

Browser auth flow переведён на cookie-first модель:

- email/password login ставит HttpOnly `access_token` и `refresh_token` cookies;
- `/auth/refresh` читает refresh token из cookie, сохраняет legacy body fallback и ставит новые cookies;
- `/auth/logout` читает access/refresh tokens из cookies или compatibility fallback и удаляет текущие + legacy auth cookies;
- frontend больше не хранит JWT в Zustand и не читает/пишет `astrotype_token` / `astrotype_refresh_token`;
- default browser API client всегда использует `credentials: "include"`, не добавляет Bearer header и делает один cookie-refresh retry при `401`;
- report API helpers больше не принимают token parameters;
- report page не очищает уже загруженный отчёт при позднем polling `401`, а показывает read-only session-expired banner;
- structural checks запрещают возврат JS JWT как browser source of truth.

CSRF baseline для MVP: `SameSite=Lax`, `Secure=true` в production, OAuth state/PKCE и trusted credentialed CORS. Double-submit CSRF для mutating endpoints оставлен для E8 production security hardening, чтобы не смешивать auth consistency cleanup с отдельным security framework.

## Что уже было сделано hotfix-коммитом

Коммит: `2eba514 fix: tolerate stale auth headers`

| Файл | Что сделано |
|---|---|
| `backend/app/dependencies.py` | `get_current_user` проверяет token candidates: Authorization, `access_token`, `astrotype_token`; stale Bearer больше не ломает валидную cookie-session. |
| `backend/app/modules/auth/router.py` | `/auth/refresh` может брать refresh token из body или cookie `refresh_token` / `astrotype_refresh_token`; ответ ставит HttpOnly `access_token` и `refresh_token`. |
| `backend/app/modules/auth/schemas.py` | Добавлен `RefreshRequest` с optional tokens для совместимости. |
| `frontend/src/lib/auth-session.ts` | Frontend больше не делает ранний logout только потому, что JS не видит refresh token; сначала вызывается cookie-aware refresh. |
| `backend/tests/unit/test_dependencies.py` | Regression test: stale Authorization header + valid cookie должен авторизовать пользователя. |

## Реализованный scope

### 1. Backend: login ставит HttpOnly cookies

`POST /api/v1/auth/login` теперь:

- валидирует email/password;
- создаёт access/refresh JWT;
- ставит:
  - `Set-Cookie: access_token=...; HttpOnly; SameSite=Lax; Path=/`;
  - `Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax; Path=/`;
- сохраняет минимально совместимый `TokenResponse` body на переходный период, но browser frontend больше не читает tokens из JSON.

### 2. Backend: refresh cookie-native

`POST /api/v1/auth/refresh`:

- читает `refresh_token` из HttpOnly cookie;
- body token используется только как legacy fallback;
- refresh token ротируется сервисом;
- ответ ставит новые HttpOnly cookies;
- при отсутствии/протухании refresh token возвращает `401`.

### 3. Backend: logout чистит cookies

`POST /api/v1/auth/logout`:

- читает текущий access token из cookie или Authorization fallback;
- читает refresh token из cookie/body fallback;
- blacklist/revoke выполняется через существующий `AuthService.logout`;
- удаляет `access_token` и `refresh_token` cookies;
- удаляет legacy `astrotype_token` и `astrotype_refresh_token` cookies на переходном этапе.

### 4. Frontend: JWT убран из auth store

`frontend/src/stores/auth-store.ts` хранит только session/user state:

```ts
type AuthState = {
  user: User | null;
  isAuthenticated: boolean;
  isLoadingSession: boolean;
};
```

Удалено из browser flow:

- `token: string | null` как источник правды;
- `setTokens(...)` как обязательный frontend step;
- запись `astrotype_token` / `astrotype_refresh_token` после login/refresh;
- token parameters в обычных API calls.

### 5. Frontend API client: protected fetch только через cookies

`frontend/src/lib/api-client.ts`:

- всегда отправляет `credentials: "include"`;
- не добавляет `Authorization` для browser app;
- при `401` делает один `POST /api/v1/auth/refresh`;
- после успешного refresh повторяет исходный request один раз;
- после неуспешного refresh отдаёт исходный auth error вызывающему UI.

Bearer support на backend сохранён для external API clients, но больше не используется как default browser mode.

### 6. Session bootstrap

`frontend/src/lib/auth-session.ts`:

1. вызывает `GET /api/v1/users/me` с `credentials: "include"`;
2. если `200` — session valid, заполняет `user`;
3. если `401` — вызывает `/auth/refresh`;
4. если refresh `200` — повторяет `/users/me`;
5. если снова `401` — очищает только UI state.

Dashboard использует этот bootstrap после OAuth/email login.

### 7. Report page не пустеет от позднего 401

Даже при истёкшей сессии UI остаётся устойчивым:

- если report уже загружен, поздний polling `401` не очищает `data/currentReport`;
- показывается banner: `Сессия истекла. Войдите снова, чтобы обновить отчёт.`;
- уже загруженный report остаётся видимым read-only;
- retry/refresh actions требуют re-login.

### 8. CSRF policy

MVP baseline:

- `SameSite=Lax` для auth cookies;
- `Secure=true` в production;
- state/PKCE для OAuth;
- CORS `allow_credentials=true` только для доверенных origins.

Production hardening follow-up в E8 scope:

- double-submit CSRF token для mutating endpoints (`POST/PATCH/DELETE`), особенно:
  - payments;
  - account settings;
  - password change;
  - logout;
  - report generation/regeneration.

## Затронутые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/auth/router.py` | Login/refresh/logout переведены на cookie-native responses; добавлены helpers для set/delete auth cookies. |
| `backend/app/dependencies.py` | Candidate-token fallback оставлен для compatibility; browser contract теперь cookie-first. |
| `backend/app/modules/auth/schemas.py` | Existing `RefreshRequest` оставлен совместимым: body token optional, cookie fallback основной для browser flow. |
| `backend/app/core/security.py` | Сроки жизни/JTI используются существующим token layer без изменения. |
| `backend/app/core/token_blacklist.py` | TTL blacklist остаётся достаточным для access/refresh logout flow. |
| `frontend/src/stores/auth-store.ts` | JWT state удалён; остались user/session/loading state. |
| `frontend/src/lib/cookies.ts` | Auth token helpers удалены; файл оставлен как non-auth placeholder. |
| `frontend/src/lib/auth-session.ts` | Cookie-native session bootstrap/refresh helper. |
| `frontend/src/lib/api-client.ts` | Default Bearer injection удалён; добавлен single cookie refresh retry. |
| `frontend/src/lib/api/report.ts` | Token parameters удалены из report API helpers. |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Поздний polling `401` больше не очищает report data; показывает banner. |
| `frontend/src/app/(auth)/login/page.tsx` | После login использует cookies + `/users/me`, не пишет JWT. |
| `frontend/src/app/(auth)/register/page.tsx` | OAuth complete-profile использует cookie session, без Authorization header из store. |
| `frontend/src/app/(dashboard)/dashboard/page.tsx` | Session bootstrap и protected fetch используют cookies. |
| `frontend/src/app/(dashboard)/products/self/page.tsx` | Protected fetch использует cookies. |
| `frontend/src/app/(dashboard)/products/career/page.tsx` | Protected fetch/report generation используют cookies. |
| `frontend/src/app/(dashboard)/settings/page.tsx` | Mutating settings calls используют cookies. |
| `frontend/src/components/layout/sidebar.tsx` | Logout вызывает backend cookie logout и затем очищает UI state. |
| `frontend/src/hooks/use-api.ts` | Generic API hooks больше не передают token. |
| `frontend/src/hooks/use-auth.ts` | Hook больше не возвращает token. |
| `frontend/scripts/check-auth-ux.mjs` | Structural checks на отсутствие JS JWT как browser source of truth. |
| `backend/tests/unit/test_auth_router_cookie.py` | Cookie login/refresh/logout regression tests. |

## Критерии приёмки

- [x] Hotfix: stale `Authorization` header не затеняет валидную cookie-backed session.
- [x] Hotfix: `/auth/refresh` умеет брать refresh token из cookies.
- [x] `POST /api/v1/auth/login` ставит HttpOnly `access_token` и `refresh_token` cookies.
- [x] Browser frontend не пишет `astrotype_token` / `astrotype_refresh_token` после login/refresh.
- [x] Zustand auth store не содержит JWT token как источник правды.
- [x] Protected browser API calls не требуют token parameter.
- [x] `/auth/refresh` cookie-native и ротирует refresh token.
- [x] `/auth/logout` удаляет HttpOnly cookies и legacy `astrotype_*` cookies.
- [x] `GET /api/v1/users/me` используется для session bootstrap.
- [x] Report page сохраняет уже загруженный report при позднем polling `401`.
- [x] Regression tests покрывают stale Bearer + valid cookie, cookie refresh, login Set-Cookie, logout delete-cookie.
- [x] Frontend structural checks запрещают default browser Bearer injection.
- [x] CSRF policy задокументирована; production double-submit CSRF вынесен в E8 security hardening scope.

## Verification commands

Фактически прогнано:

Backend targeted:

```bash
.venv/bin/python -m ruff check backend/app/modules/auth/router.py backend/tests/unit/test_auth_router_cookie.py backend/app/dependencies.py backend/tests/unit/test_dependencies.py
.venv/bin/python -m pytest backend/tests/unit/test_auth_router_cookie.py backend/tests/unit/test_dependencies.py -q
```

Result: ruff passed; pytest `6 passed`.

Frontend targeted:

```bash
cd frontend
npm test
npx eslint .
npx tsc --noEmit
```

Result: `check-report-ux`, `check-auth-ux`, `check-billing-ux`, eslint and TypeScript passed.

Note: `npm run lint` currently maps to `next lint`, which is not compatible with the installed Next 16 CLI shape in this project (`Invalid project directory provided .../frontend/lint`). `npx eslint .` is the effective lint command used for this story.

## Live smoke checklist

```bash
# 1. login sets cookies
curl -i -X POST http://localhost:3000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  --data '{"email":"...","password":"..."}'

# Expected: Set-Cookie access_token + refresh_token with HttpOnly.

# 2. protected endpoint works with cookies only
curl -i 'http://localhost:3000/api/v1/reports?product=self&limit=100' \
  -H 'Cookie: access_token=<valid>'

# Expected: 200.

# 3. stale Authorization must not shadow valid cookie
curl -i 'http://localhost:3000/api/v1/reports?product=self&limit=100' \
  -H 'Authorization: Bearer stale.invalid.token' \
  -H 'Cookie: access_token=<valid>'

# Expected: 200.

# 4. refresh works with cookie only
curl -i -X POST http://localhost:3000/api/v1/auth/refresh \
  -H 'Cookie: refresh_token=<valid>' \
  --data '{}'

# Expected: 200 + rotated cookies.
```

Browser smoke:

1. Login by email/password.
2. Open `/report/<profile_id>`.
3. Confirm DevTools Network has no repeated `401` on `/api/v1/reports?product=self&limit=100`.
4. Confirm frontend storage has no JS-readable `astrotype_token` / `astrotype_refresh_token` dependency.
5. Let polling run for 15–30 seconds; report must not blank.

## Non-goals

- Не переписывать email verification/password reset.
- Не ломать external API clients that explicitly use `Authorization: Bearer`.
- Не убирать Bearer support из backend полностью.
- Не внедрять полный CSRF framework без отдельной production-hardening story.

## Примечания

Эта story закрывает auth consistency для browser app и report-page blank/401 bug class. Она не заменяет E8 security hardening: CSRF, WAF, security headers и production audit должны идти отдельными задачами.
