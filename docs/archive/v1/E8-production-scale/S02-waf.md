# Story E8.S02: WAF (Web Application Firewall)

**Feature:** [Production & Scale](Archemap/docs/features/v1/E8-production-scale/FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Защита от SQL injection, XSS, path traversal, и других атак на уровне reverse proxy.

## Что сделать

- Nginx/Caddy WAF rules
- ModSecurity или Coraza WAF engine
- OWASP Core Rule Set (CRS)
- Блокировка подозрительных запросов
- Логирование заблокированных запросов

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `infra/nginx/waf.conf` | Nginx WAF configuration |
| `infra/nginx/modsecurity.conf` | ModSecurity rules |
| `docker-compose.yml` | Nginx service with WAF |

## Правила

| Тип атаки | Правило |
|---|---|
| SQL Injection | CRS 942100-942999 |
| XSS | CRS 941100-941999 |
| Path Traversal | CRS 930100-930999 |
| Remote Code Execution | CRS 932100-932999 |
| HTTP Protocol Violation | CRS 920100-920999 |

## Критерии приёмки

- [ ] Nginx reverse proxy с ModSecurity
- [ ] OWASP CRS подключены
- [ ] Блокировка SQLi, XSS, path traversal
- [ ] Whitelist для healthcheck endpoints
- [ ] Логирование заблокированных запросов
- [ ] Тесты (попытки атак → 403)

## Примечания

- Для начала: Caddy с fail2ban (простой вариант)
- Потом: Nginx + ModSecurity + CRS (полный WAF)
- Cloudflare как альтернатива (managed WAF)
