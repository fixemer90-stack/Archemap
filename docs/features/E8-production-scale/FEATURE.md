# Feature E8: Production & Scale

## Цель

Production-ready: rate limiting, WAF, secrets management, observability, load testing, K8s деплой, GitOps.

## Зависимости

`E6`, `E7`

## Критерии приёмки

- [x] Rate limiting: login 5 req/15min, geocode 30 req/min (частично)
- [ ] Rate limiting: глобальный 100 req/min/user
- [ ] WAF: блокировка SQLi, XSS, path traversal
- [ ] Secrets: централизованный manager, ротация через CI
- [ ] Observability: traces (Jaeger), metrics (Grafana), logs (Loki)
- [ ] Load testing: 500 concurrent, p95 < 500ms
- [ ] K8s: Yandex Managed, autoscaling, rolling updates
- [ ] GitOps: Argo CD, push-to-deploy, rollback через revert
- [ ] Render: описан и подготовлен MVP-деплой frontend/backend/worker + managed Postgres + managed Redis/Valkey
- [ ] Object storage strategy для managed deploy зафиксирована: внешний S3-compatible provider или отдельный storage-refactor, без скрытой зависимости на локальный диск

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Rate limiting API](S01-rate-limiting-api.md) | ✅ Готово |
| S02 | [WAF](S02-waf.md) | ⬜ Не начато |
| S03 | [Secrets manager](S03-secrets-manager.md) | ✅ Готово |
| S04 | [Observability](S04-observability.md) | 🟡 Частично |
| S05 | [Load testing](S05-load-testing.md) | ⬜ Не начато |
| S06 | [K8s deploy](S06-k8s-deploy.md) | ⬜ Не начато |
| S07 | [GitOps](S07-gitops.md) | ⬜ Не начато |
| S08 | [Render deploy](S08-render-deploy.md) | ⬜ Не начато |
| S09 | [Artifact storage strategy for Render / S3 replacement](S09-artifact-storage-strategy.md) | ⬜ Не начато |

## Текущее состояние

### Что уже есть

- **Rate limiting**: Redis-backed token bucket для login (5 req/15min) и geocode (30 req/min per IP)
- **Observability**: OpenTelemetry instrumentation (FastAPI), structlog JSON logs
- **Production guards**: SECRET_KEY не может быть "change-me" в production
- **Security**: HttpOnly cookies, token blacklist, OAuth state validation
- **CI/CD**: GitHub Actions (lint, test, build, deploy)
- **Render-ready story baseline**: в docs уже зафиксировано, что backend и worker ложатся в Render естественно, а frontend пока зависит от живого Next server из-за rewrites `/api/* -> BACKEND_URL`

### Что нужно для production

- Глобальный rate limiting (все endpoints, не только auth)
- WAF (nginx/Caddy rules или Cloudflare)
- Secrets management (Vault, AWS SSM, или Yandex Lockbox)
- Distributed tracing (Jaeger/Tempo)
- Metrics (Prometheus + Grafana)
- Load testing (k6, Locust)
- Render-ready blueprint для MVP-деплоя: backend web service, worker, managed Postgres, managed Redis/Valkey, отдельное решение по frontend (static vs web service)
- Явная стратегия object storage для managed deploy: внешний S3-compatible provider как быстрый MVP путь либо отдельный refactor, если продукт хочет уйти от S3-интерфейса полностью
- K8s deployment (Yandex Managed Kubernetes)
- GitOps (Argo CD)
