# E2 Identity Auth API Contract

Этот документ фиксирует целевой API contract для cookie-first browser authentication в Astrotype.

Текущее фактическое состояние реализации: [CURRENT-AUTH-FLOW.md](CURRENT-AUTH-FLOW.md).

Base path: `/api/v1`

## Token/cookie names

### Target browser cookies

| Cookie          | Purpose                              | JS-readable | HttpOnly | Lifetime                          | Notes                          |
| --------------- | ------------------------------------ | ----------: | -------: | --------------------------------- | ------------------------------ |
| `access_token`  | short-lived JWT for protected routes |          no |      yes | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Sent automatically by browser. |
| `refresh_token` | long-lived JWT for refresh           |          no |      yes | `JWT_REFRESH_TOKEN_EXPIRE_DAYS`   | Rotated on refresh.            |

### Legacy migration cookies

| Cookie                    | Status                  | Notes                                                           |
| ------------------------- | ----------------------- | --------------------------------------------------------------- |
| `astrotype_token`         | legacy / migration only | JS-readable; must not be source of truth in final browser flow. |
| `astrotype_refresh_token` | legacy / migration only | JS-readable; remove after frontend migration.                   |

Backend may accept legacy cookies during migration, but frontend must stop writing them for browser auth.

## Authorization methods

| Method                   | Intended consumer                          | Priority           |
| ------------------------ | ------------------------------------------ | ------------------ |
| HttpOnly cookies         | Browser web app                            | Primary            |
| `Authorization: Bearer`  | API clients, tests, backward compatibility | Fallback           |
| `astrotype_*` JS cookies | Migration compatibility only               | Temporary fallback |

Protected backend dependency must treat tokens as candidates:

1. `Authorization: Bearer <token>`
2. `access_token` cookie
3. `astrotype_token` cookie

It must accept the first valid, non-blacklisted token. A stale Bearer header must not force `401` if a valid cookie is present.

## POST /auth/login

Authenticate with email/password.

### Request

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "correct horse battery staple"
}
```

### Target response

```http
HTTP/1.1 200 OK
Set-Cookie: access_token=<jwt>; HttpOnly; Path=/; SameSite=Lax; Max-Age=1800
Set-Cookie: refresh_token=<jwt>; HttpOnly; Path=/; SameSite=Lax; Max-Age=2592000
Content-Type: application/json
```

```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User",
    "is_active": true,
    "is_verified": true
  }
}
```

### Transitional response allowed

During migration, backend may continue returning:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

But browser frontend must not depend on these fields. API clients may continue using them.

### Errors

| Status | Reason                                    |
| -----: | ----------------------------------------- |
|    401 | Invalid email/password, inactive account. |
|    403 | Email not verified.                       |
|    429 | Login rate limit exceeded.                |

## POST /auth/refresh

Issue new tokens using refresh cookie.

### Request — target browser flow

```http
POST /api/v1/auth/refresh
Cookie: refresh_token=<jwt>
Content-Type: application/json
```

```json
{}
```

### Request — legacy fallback

```json
{
  "refresh_token": "legacy-js-readable-refresh-token",
  "token_type": "bearer"
}
```

### Response

```http
HTTP/1.1 200 OK
Set-Cookie: access_token=<new-jwt>; HttpOnly; Path=/; SameSite=Lax; Max-Age=1800
Set-Cookie: refresh_token=<new-jwt>; HttpOnly; Path=/; SameSite=Lax; Max-Age=2592000
Content-Type: application/json
```

Target browser body:

```json
{
  "ok": true
}
```

Transitional body:

```json
{
  "access_token": "new-access-token",
  "refresh_token": "new-refresh-token",
  "token_type": "bearer"
}
```

### Rules

- Read refresh token from `refresh_token` cookie first.
- Accept body `refresh_token` only as legacy fallback.
- Blacklist/revoke old refresh token jti before issuing a new one.
- Return `401` if no valid refresh token exists.
- Do not require JavaScript to read refresh token.

## POST /auth/logout

End current session.

### Request

```http
POST /api/v1/auth/logout
Cookie: access_token=<jwt>; refresh_token=<jwt>
```

Optional compatibility header:

```http
Authorization: Bearer <access-token>
```

### Response

```http
HTTP/1.1 200 OK
Set-Cookie: access_token=; Max-Age=0; Path=/
Set-Cookie: refresh_token=; Max-Age=0; Path=/
Set-Cookie: astrotype_token=; Max-Age=0; Path=/
Set-Cookie: astrotype_refresh_token=; Max-Age=0; Path=/
Content-Type: application/json
```

```json
{
  "message": "Logged out successfully."
}
```

### Rules

- Blacklist access jti if a valid access token is available.
- Blacklist refresh jti if a valid refresh token is available.
- Always clear cookies even if token was already expired.
- Frontend clears only local `user/session` state, not JWT.

## GET /users/me

Session bootstrap endpoint.

### Request

```http
GET /api/v1/users/me
Cookie: access_token=<jwt>
```

### Response

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User",
  "is_active": true,
  "is_verified": true
}
```

### Frontend bootstrap logic

1. Call `/users/me` with `credentials: "include"`.
2. If `200`, set `user` and `isAuthenticated=true`.
3. If `401`, call `/auth/refresh` once.
4. If refresh succeeds, repeat `/users/me` once.
5. If still `401`, set `user=null` and `isAuthenticated=false`.

## Protected report endpoints

These endpoints must work with cookies only:

- `GET /api/v1/profiles/{profile_id}`
- `POST /api/v1/profiles/{profile_id}/chart`
- `GET /api/v1/reports?product=self&limit=100`
- `GET /api/v1/reports/{report_id}`
- `POST /api/v1/reports/generate`
- `POST /api/v1/reports/{report_id}/narrative/regenerate`
- `GET /api/v1/reports/{report_id}/pdf`

### Required regression

```http
GET /api/v1/reports?product=self&limit=100
Authorization: Bearer stale.invalid.token
Cookie: access_token=<valid-token>
```

Expected: `200 OK`, not `401`.

## Frontend API-client contract

Browser mode:

```ts
await fetch("/api/v1/reports?product=self&limit=100", {
  credentials: "include",
});
```

Browser mode must not default to:

```ts
headers.Authorization = `Bearer ${token}`;
```

If a dedicated API-client mode is needed for external clients/tests, it must be explicit and isolated from browser app code.

## CSRF notes

Cookie auth needs explicit CSRF posture.

MVP:

- `SameSite=Lax` cookies;
- `Secure=true` in production;
- strict CORS origins;
- OAuth state validation.

Production hardening:

- add CSRF token/double-submit protection for mutating browser endpoints;
- document exceptions for pure API-client Bearer mode.

## Acceptance API smoke

```bash
# stale bearer must not shadow valid cookie
curl -i 'http://localhost:3000/api/v1/reports?product=self&limit=100' \
  -H 'Authorization: Bearer stale.invalid.token' \
  -H 'Cookie: access_token=<valid>'

# cookie-native refresh
curl -i -X POST 'http://localhost:3000/api/v1/auth/refresh' \
  -H 'Cookie: refresh_token=<valid>' \
  -H 'Content-Type: application/json' \
  --data '{}'
```
