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

## Текущее состояние

### Что уже есть

- **Rate limiting**: Redis-backed token bucket для login (5 req/15min) и geocode (30 req/min per IP)
- **Observability**: OpenTelemetry instrumentation (FastAPI), structlog JSON logs
- **Production guards**: SECRET_KEY не может быть "change-me" в production
- **Security**: HttpOnly cookies, token blacklist, OAuth state validation
- **CI/CD**: GitHub Actions (lint, test, build, deploy)

### Что нужно для production

- Глобальный rate limiting (все endpoints, не только auth)
- WAF (nginx/Caddy rules или Cloudflare)
- Secrets management (Vault, AWS SSM, или Yandex Lockbox)
- Distributed tracing (Jaeger/Tempo)
- Metrics (Prometheus + Grafana)
- Load testing (k6, Locust)
- K8s deployment (Yandex Managed Kubernetes)
- GitOps (Argo CD)
