# Feature E8: Production & Scale

## Цель

Production-ready: rate limiting, WAF, secrets management, observability, load testing, K8s деплой, GitOps.

## Зависимости

`E6`, `E7`

## Критерии приёмки

- [ ] Rate limiting: 100 req/min/user, 10 req/min auth
- [ ] WAF: блокировка SQLi, XSS, path traversal
- [ ] Secrets: централизованный manager, ротация через CI
- [ ] Observability: traces (Jaeger), metrics (Grafana), logs (Loki)
- [ ] Load testing: 500 concurrent, p95 < 500ms
- [ ] K8s: Yandex Managed, autoscaling, rolling updates
- [ ] GitOps: Argo CD, push-to-deploy, rollback через revert

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Rate limiting API](S01-rate-limiting-api.md) | ⬜ Не начато |
| S02 | [WAF](S02-waf.md) | ⬜ Не начато |
| S03 | [Secrets manager](S03-secrets-manager.md) | ⬜ Не начато |
| S04 | [Observability](S04-observability.md) | ⬜ Не начато |
| S05 | [Load testing](S05-load-testing.md) | ⬜ Не начато |
| S06 | [K8s deploy](S06-k8s-deploy.md) | ⬜ Не начато |
| S07 | [GitOps](S07-gitops.md) | ⬜ Не начато |
