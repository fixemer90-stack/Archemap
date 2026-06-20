# Story E2.10: Cookie-first session auth cleanup

**Feature:** [Authentication & Identity](FEATURE.md)
**Статус:** 🟡 В процессе

## Контекст

В текущем frontend/backend auth flow исторически смешаны две модели:

1. JS-managed JWT:
   - `astrotype_token`
   - `astrotype_refresh_token`
   - frontend читает токены через `js-cookie` и отправляет `Authorization: Bearer ...`.

2. Cookie-backed JWT session:
   - `access_token`
   - `refresh_token`
   - OAuth/Yandex ставит HttpOnly cookies;
   - browser отправляет cookies через `credentials: "include"`.

Из-за этого появился классический auth-flap: frontend мог отправить протухший Bearer header, backend проверял его первым и возвращал `401`, хотя в cookies могла быть валидная сессия. На report page это проявлялось как поздний `401` на `/api/v1/reports?product=self&limit=100`, сброс состояния и пустой экран.

Текущий hotfix уже делает backend устойчивее: `get_current_user` проверяет токены как candidates и не даёт stale Bearer header затенить валидную cookie. Но целевая архитектура должна быть cookie-first: browser app не хранит JWT в JS-readable cookies/localStorage и не носит access token вручную.

## Цель

Перевести browser auth flow на взрослую cookie-first session model:

- HttpOnly cookies — основной источник авторизации для web app;
- `Authorization: Bearer` остаётся только compatibility/API-client fallback;
- frontend хранит user/session state, а не JWT;
- login/OAuth/refresh/logout работают единообразно;
- report page и другие protected screens не зависят от JS-readable token.

## Что уже сделано hotfix-коммитом

Коммит: `2eba514 fix: tolerate stale auth headers`

| Файл | Что сделано |
|---|---|
| `backend/app/dependencies.py` | `get_current_user` проверяет token candidates: Authorization, `access_token`, `astrotype_token`; stale Bearer больше не ломает валидную cookie-session. |
| `backend/app/modules/auth/router.py` | `/auth/refresh` может брать refresh token из body или cookie `refresh_token` / `astrotype_refresh_token`; ответ ставит HttpOnly `access_token` и `refresh_token`. |
| `backend/app/modules/auth/schemas.py` | Добавлен `RefreshRequest` с optional tokens для совместимости. |
| `frontend/src/lib/auth-session.ts` | frontend больше не делает ранний logout только потому, что JS не видит refresh token; сначала вызывается cookie-aware refresh. |
| `backend/tests/unit/test_dependencies.py` | Добавлен regression test: stale Authorization header + valid cookie должен авторизовать пользователя. |

## Что сделать дальше

### 1. Backend: login должен ставить HttpOnly cookies

Сейчас обычный email/password login возвращает JWT в JSON. Целевое поведение:

- `POST /api/v1/auth/login` валидирует email/password;
- backend создаёт access/refresh JWT;
- backend ставит:
  - `Set-Cookie: access_token=...; HttpOnly; SameSite=Lax; Path=/`
  - `Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax; Path=/`
- body возвращает session/user metadata без JWT либо минимально совместимый payload на переходный период.

Compatibility note: если внешние API-клиенты уже читают JSON tokens, оставить временный response shape, но browser frontend не должен на него полагаться.

### 2. Backend: refresh должен стать cookie-native

Целевое поведение:

- `POST /api/v1/auth/refresh` читает `refresh_token` из HttpOnly cookie;
- body token используется только как legacy fallback;
- refresh token ротируется;
- старый refresh token blacklist/revoke;
- ответ ставит новые cookies;
- при отсутствии/протухании refresh cookie возвращает `401` без частичного UI logout на backend.

### 3. Backend: logout должен чистить cookies

Целевое поведение:

- `POST /api/v1/auth/logout` читает текущий access token из cookie или Authorization fallback;
- blacklist/revoke текущий access token;
- blacklist/revoke refresh token, если доступен;
- `delete_cookie("access_token")`;
- `delete_cookie("refresh_token")`;
- legacy `astrotype_*` cookies удаляются на переходном этапе.

### 4. Frontend: убрать JWT из auth store

`frontend/src/stores/auth-store.ts` должен хранить только session/user state:

```ts
type AuthState = {
  user: User | null;
  isAuthenticated: boolean;
  isLoadingSession: boolean;
};
```

Удалить из browser flow:

- `token: string | null` как источник правды;
- `setTokens(...)` как обязательный frontend step;
- запись `astrotype_token` / `astrotype_refresh_token` после login/refresh;
- token parameters в обычных API calls.

### 5. Frontend API client: protected fetch только через cookies

`frontend/src/lib/api-client.ts`:

- всегда `credentials: "include"`;
- не добавляет `Authorization` для browser app;
- при `401` делает один `POST /api/v1/auth/refresh`;
- после успешного refresh повторяет исходный request один раз;
- после второго `401` отдаёт понятную ошибку session expired.

Bearer support можно оставить отдельным explicit API-client mode, но не как default browser mode.

### 6. Session bootstrap

При старте dashboard/auth provider:

1. `GET /api/v1/users/me` с `credentials: "include"`.
2. Если `200` — session valid, заполнить `user`.
3. Если `401` — вызвать `/auth/refresh`.
4. Если refresh `200` — повторить `/users/me`.
5. Если снова `401` — session expired, очистить только UI state.

### 7. Report page не должен пустеть от позднего 401

Даже при правильном auth flow UI должен быть устойчивым:

- если report уже загружен, поздний polling `401` не должен очищать `data/currentReport`;
- показать banner: `Сессия истекла. Войдите снова, чтобы обновить отчёт.`;
- уже загруженный report остаётся видимым read-only;
- retry/refresh actions требуют re-login.

### 8. CSRF policy

Поскольку browser auth живёт в cookies, нужна явная CSRF-политика:

MVP baseline:

- `SameSite=Lax` для auth cookies;
- `Secure=true` в production;
- state/PKCE для OAuth;
- CORS `allow_credentials=true` только для доверенных origins.

Production hardening:

- double-submit CSRF token для mutating endpoints (`POST/PATCH/DELETE`), особенно:
  - payments;
  - account settings;
  - password change;
  - logout;
  - report generation/regeneration.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/auth/router.py` | Изменить login/refresh/logout на cookie-native responses. |
| `backend/app/modules/auth/schemas.py` | Разделить request/response schemas для login/refresh/session metadata. |
| `backend/app/dependencies.py` | Оставить candidate-token fallback, но cookie-first сделать основным browser contract. |
| `backend/app/core/security.py` | Проверить сроки жизни access/refresh tokens и jti для rotation/blacklist. |
| `backend/app/core/token_blacklist.py` | Проверить blacklist TTL для access/refresh. |
| `frontend/src/stores/auth-store.ts` | Убрать хранение JWT, оставить user/session state. |
| `frontend/src/lib/cookies.ts` | Удалить или оставить только non-auth helpers; не читать JWT из JS для browser flow. |
| `frontend/src/lib/auth-session.ts` | Переделать в cookie-native session bootstrap/refresh helper. |
| `frontend/src/lib/api-client.ts` | Убрать default Bearer injection, добавить single refresh retry. |
| `frontend/src/lib/api/report.ts` | Убрать token parameters из report API helpers. |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Не очищать report data на поздний 401 polling. |
| `frontend/src/app/(auth)/login/page.tsx` | После login полагаться на cookies + `/users/me`, не писать JWT. |
| `frontend/src/app/(auth)/auth/callback/page.tsx` | OAuth callback уже cookie-backed; синхронизировать session bootstrap. |
| `frontend/scripts/check-auth-ux.mjs` | Добавить structural checks на отсутствие JS JWT как browser source of truth. |
| `frontend/scripts/check-report-ux.mjs` | Проверить, что report page не зависит от `token` и не очищает data на polling 401. |

## Критерии приёмки

- [x] Hotfix: stale `Authorization` header не затеняет валидную cookie-backed session.
- [x] Hotfix: `/auth/refresh` умеет брать refresh token из cookies.
- [ ] `POST /api/v1/auth/login` ставит HttpOnly `access_token` и `refresh_token` cookies.
- [ ] Browser frontend не пишет `astrotype_token` / `astrotype_refresh_token` после login/refresh.
- [ ] Zustand auth store не содержит JWT token как источник правды.
- [ ] Protected browser API calls не требуют token parameter.
- [ ] `/auth/refresh` cookie-native и ротирует refresh token.
- [ ] `/auth/logout` удаляет HttpOnly cookies и legacy `astrotype_*` cookies.
- [ ] `GET /api/v1/users/me` используется для session bootstrap.
- [ ] Report page сохраняет уже загруженный report при позднем polling `401`.
- [ ] Regression tests покрывают stale Bearer + valid cookie, cookie refresh, login Set-Cookie, logout delete-cookie.
- [ ] Frontend structural checks запрещают default browser Bearer injection.
- [ ] CSRF policy задокументирована и для production mutating endpoints заведена отдельная story/задача, если не реализуется в рамках этой.

## Verification commands

Backend targeted:

```bash
docker compose exec -T backend sh -lc '
  cd /app &&
  python -m ruff check app/dependencies.py app/modules/auth/router.py app/modules/auth/schemas.py tests/unit/test_dependencies.py &&
  python -m ruff format --check app/dependencies.py app/modules/auth/router.py app/modules/auth/schemas.py tests/unit/test_dependencies.py &&
  python -m mypy app/dependencies.py app/modules/auth/router.py app/modules/auth/schemas.py &&
  python -m pytest tests/unit/test_dependencies.py -q
'
```

Frontend targeted:

```bash
cd frontend
npx tsc --noEmit --pretty false
npx prettier --check src/lib/auth-session.ts src/lib/api-client.ts src/stores/auth-store.ts
npx eslint src/lib/auth-session.ts src/lib/api-client.ts src/stores/auth-store.ts
node scripts/check-auth-ux.mjs
node scripts/check-report-ux.mjs
```

Live smoke:

```bash
# 1. login sets cookies
curl -i -X POST http://localhost:3000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  --data '{"email":"...","password":"..."}'

# Expected: Set-Cookie access_token + refresh_token with HttpOnly.

# 2. protected endpoint works with cookies only
curl -i http://localhost:3000/api/v1/reports?product=self\&limit=100 \
  -H 'Cookie: access_token=<valid>'

# Expected: 200.

# 3. stale Authorization must not shadow valid cookie
curl -i http://localhost:3000/api/v1/reports?product=self\&limit=100 \
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
4. Clear JS-readable `astrotype_token` manually; report must still load if HttpOnly session is valid.
5. Force stale Bearer in legacy state if compatibility code still exists; valid cookie must still win.
6. Let polling run for 15–30 seconds; report must not blank.

## Non-goals

- Не переписывать email verification/password reset.
- Не ломать external API clients that explicitly use `Authorization: Bearer`.
- Не убирать Bearer support из backend полностью.
- Не внедрять полный CSRF framework без отдельной production-hardening story, если scope становится слишком большим.

## Примечания

Эта story закрывает auth consistency для browser app и report-page blank/401 bug class. Она не заменяет E8 security hardening: CSRF, WAF, security headers и production audit должны идти отдельными задачами.
