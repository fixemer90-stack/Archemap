# Production VPS deployment

Target for first production release:

- Domain: `astrotype.ru`, `www.astrotype.ru`
- VPS: Ubuntu with root access
- Runtime: Docker Compose
- Public ingress: Caddy on ports 80/443 with automatic Let's Encrypt TLS
- Internal services: Next.js frontend, FastAPI backend, Celery worker, PostgreSQL, Redis

## DNS

At the registrar/DNS provider set:

```text
A  @    46.173.16.113
A  www  46.173.16.113
```

Verify from any shell:

```bash
python3 - <<'PY'
import socket
for host in ['astrotype.ru', 'www.astrotype.ru']:
    print(host, socket.gethostbyname_ex(host)[2])
PY
```

Both hosts must resolve to the VPS IP before Caddy can issue certificates.

## Server bootstrap

Docker Engine and Compose are required:

```bash
docker --version
docker compose version
systemctl is-active docker
```

Ports 80 and 443 must be reachable from the internet. Keep SSH open.

## Files on server

Deploy the repository to:

```text
/opt/astrotype
```

Create the untracked production environment file:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Fill production secrets. Do not commit `.env.production`.

Required values:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `YANDEX_CLIENT_ID` / `YANDEX_CLIENT_SECRET` when OAuth is enabled
- `LLM_API_KEY` when real DeepSeek generation is enabled
- SMTP values if `EMAIL_PROVIDER=smtp`

## Start/update

```bash
cd /opt/astrotype
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

The backend container runs migrations before starting FastAPI:

```text
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## Health checks

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
curl -fsS https://astrotype.ru/api/v1/health
curl -fsSI https://astrotype.ru/
```

Expected:

- Caddy is listening on public 80/443.
- Backend, frontend, Postgres, Redis are healthy/running.
- `https://astrotype.ru/api/v1/health` returns HTTP 200.
- Frontend returns HTTP 200.

## Logs

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production logs --tail=200 backend
docker compose -f docker-compose.prod.yml --env-file .env.production logs --tail=200 frontend
docker compose -f docker-compose.prod.yml --env-file .env.production logs --tail=200 worker
docker compose -f docker-compose.prod.yml --env-file .env.production logs --tail=200 caddy
```

## Backups

Database volume backup:

```bash
cd /opt/astrotype
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "backups/postgres-$stamp.sql"
```

Before destructive migrations or deploys, take a VPS snapshot in the provider panel.
