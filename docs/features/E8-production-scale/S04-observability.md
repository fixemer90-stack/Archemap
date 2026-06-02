# Story E8.S04: Observability

**Feature:** [Production & Scale](FEATURE.md)
**Статус:** 🟡 Частично

## Контекст

Полный observability stack: traces, metrics, logs. Мониторинг производительности и ошибок.

## Что сделать

### Уже реализовано

- OpenTelemetry instrumentation (FastAPI)
- structlog JSON logs
- Sentry DSN (error tracking)

### Нужно реализовать

- Distributed tracing: OpenTelemetry → Jaeger/Tempo
- Metrics: Prometheus + Grafana dashboards
- Logs: structlog → Loki (или ELK)
- Alerting: PagerDuty/Telegram alerts
- Health checks: readiness/liveness probes

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/main.py` | OpenTelemetry instrumentation (✅ есть) |
| `backend/app/config.py` | Sentry DSN (✅ есть) |
| `infra/monitoring/` | Prometheus, Grafana, Loki configs |
| `docker-compose.yml` | Monitoring services |

## Метрики для мониторинга

| Метрика | Описание | Alert |
|---|---|---|
| `http_request_duration_seconds` | Latency per endpoint | p95 > 500ms |
| `http_requests_total` | Request count per status | 5xx rate > 1% |
| `db_connection_pool_size` | Active DB connections | > 80% pool |
| `redis_connection_status` | Redis health | Down |
| `report_generation_duration` | Report generation time | > 10s |
| `auth_failures_total` | Failed auth attempts | > 10/min |

## Grafana Dashboards

| Dashboard | Панели |
|---|---|
| **API Overview** | Request rate, latency p50/p95/p99, error rate |
| **Database** | Connection pool, query duration, slow queries |
| **Redis** | Hit rate, memory usage, connection count |
| **Business** | Registrations, reports generated, active users |

## Критерии приёмки

- [x] OpenTelemetry instrumentation
- [x] structlog JSON logs
- [x] Sentry error tracking
- [ ] Jaeger/Tempo для distributed tracing
- [ ] Prometheus metrics endpoint
- [ ] Grafana dashboards
- [ ] Loki для log aggregation
- [ ] Alerting rules
- [ ] Health check probes

## Примечания

- OpenTelemetry уже интегрирован в FastAPI
- structlog уже используется во всех модулях
- Нужно добавить Prometheus exporter и Grafana dashboards
