# Story E8.S07: GitOps

**Feature:** [Production & Scale](Archemap/docs/features/v1/E8-production-scale/FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

GitOps workflow: push-to-deploy, автоматический rollback через revert, Argo CD.

## Что сделать

- Установить Argo CD
- Настроить Argo CD Applications для каждого сервиса
- Push-to-deploy: merge в main → автоматический деплой
- Rollback: revert commit → откат
- Notifications: Slack/Telegram при деплое

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `infra/argocd/` | Argo CD configuration |
| `infra/argocd/applications/` | Argo CD Application manifests |
| `.github/workflows/deploy.yml` | CI/CD pipeline |

## GitOps Flow

```
Developer → git push → GitHub Actions (CI) → Build images → Push to registry
                                                           ↓
                                        Argo CD detects new image → Deploy to K8s
                                                           ↓
                                        Health check → Success → Notify
                                                           ↓
                                        Failure → Rollback → Notify
```

## Argo CD Applications

| Application | Repo Path | K8s Namespace |
|---|---|---|
| `astrotype-backend` | `infra/k8s/backend/` | `astrotype` |
| `astrotype-frontend` | `infra/k8s/frontend/` | `astrotype` |
| `astrotype-postgres` | `infra/k8s/postgres/` | `astrotype` |
| `astrotype-redis` | `infra/k8s/redis/` | `astrotype` |

## Критерии приёмки

- [ ] Argo CD установлен и настроен
- [ ] Applications для всех сервисов
- [ ] Push-to-deploy работает
- [ ] Rollback через revert работает
- [ ] Notifications (Slack/Telegram)
- [ ] Multi-environment (staging, production)
- [ ] Secret management через Argo CD

## Примечания

- Argo CD — стандарт де-факто для GitOps
- Альтернатива: Flux CD
- Для начала: single environment (production)
- Потом: staging + production с promotion
