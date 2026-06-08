# Story E8.S08: Render Deploy

**Feature:** [Production & Scale](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Нужен первый managed deploy path без Kubernetes: Render должен стать MVP-окружением для frontend, backend, worker и managed data services.

Текущий runtime-контракт уже частично готов в коде:
- `docker-compose.yml` поднимает `backend`, `worker`, `frontend`, `postgres`, `redis`, `minio`;
- backend и worker уже разделены на разные процессы и используют общий env contract из `backend/app/config.py`;
- worker стартует через `celery -A workers.celery_app.app worker --loglevel=INFO` и обрабатывает `reports.generate_pdf` и `reports.generate_report_narrative`;
- frontend сейчас зависит от живого Next.js server: `frontend/next.config.ts` проксирует `/api/:path*` в `BACKEND_URL`, а код массово использует `/api/v1/...`.

Из этого следует текущий deploy target:
- backend = Render Web Service;
- worker = Render Background Worker;
- database = Render Managed Postgres;
- queue/cache = Render Managed Redis/Valkey;
- frontend = пока тоже Render Web Service, а не Static Site.

Pure static hosting пока не является честным MVP-целью: без отдельного refactor фронтенд потеряет server-side rewrites и сломает `/api/v1/...` contract, OAuth callbacks и cookie-auth flow.

## Решение для первого Render deploy

Для первого управляемого деплоя принимается такой service split:

- `frontend` — Render Web Service сейчас; Render Static Site только после отдельного frontend refactor;
- `backend` — Render Web Service;
- `worker` — Render Background Worker;
- `postgres` — Render Managed Postgres;
- `redis`/`valkey` — Render Managed Redis/Valkey;
- object storage — внешний S3-compatible provider, не локальный диск Render.

Это означает, что формулировка `frontend web/static` на текущем этапе должна читаться так: `web` — да, `static` — только как future target после отдельной истории на отказ от runtime rewrites.

## Что сделать

1. Зафиксировать Render blueprint (`render.yaml` или эквивалентный deployment contract) для сервисов:
   - `frontend`;
   - `backend` web service;
   - `worker` background worker;
   - managed Postgres;
   - managed Redis/Valkey.
2. Разделить текущий и целевой frontend mode:
   - текущий MVP mode: `frontend` как Render Web Service с живым Next server;
   - optional future mode: отдельная Story на refactor под Static Site с `NEXT_PUBLIC_API_URL`, прямыми CORS/cookie вызовами и отказом от `rewrites()` как runtime-критической зависимости.
3. Зафиксировать production start commands:
   - backend: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`;
   - worker: `celery -A workers.celery_app.app worker --loglevel=INFO`;
   - frontend: production Next start, а не `npm run dev`.
4. Описать production env contract:
   - `APP_ENV=production`, `SECRET_KEY`, `ALLOWED_ORIGINS`;
   - `DATABASE_URL`;
   - `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`;
   - `FRONTEND_URL`, `BACKEND_URL`, OAuth redirect URIs;
   - email, YooKassa, `LLM_*`;
   - `S3_*` для artifact storage.
5. Зафиксировать health checks и smoke probes:
   - backend health: `GET /api/v1/health`;
   - frontend: landing, login, billing;
   - worker: логи о подключении к broker и обработке `reports.generate_pdf` / `reports.generate_report_narrative`.
6. Явно описать blockers и границы Story:
   - frontend static deploy пока не готов;
   - текущие Dockerfiles dev-ориентированы и потребуют production commands/build stages;
   - external object storage не закрывается самим Render и должен идти отдельным решением из S09.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `render.yaml` | Blueprint Render для frontend/backend/worker/Postgres/Redis |
| `backend/Dockerfile` | Production build/run contract для backend image |
| `frontend/Dockerfile` | Production build/run contract для frontend image |
| `docker-compose.yml` | Источник текущего runtime-контракта |
| `backend/app/config.py` | Env contract backend/worker |
| `backend/workers/celery_app.py` | Worker runtime и broker/backend settings |
| `backend/workers/tasks/reports.py` | Задачи, которые обязан забирать Render worker |
| `frontend/next.config.ts` | Runtime rewrite-зависимость, блокирующая pure static deploy |
| `docs/features/E8-production-scale/FEATURE.md` | Статус E8 и связанная story table |
| `docs/SRS/SRS-E8-production-scale.md` | Инфраструктурный контракт уровня SRS |

## Acceptance Criteria

- [ ] В документации зафиксирован Render deployment contract для `frontend`, `backend`, `worker`, managed Postgres и managed Redis/Valkey.
- [ ] Backend start command описан как production runtime без `--reload` и использует Render `$PORT`.
- [ ] Worker описан как отдельный Render Background Worker с корректным Celery command.
- [ ] Frontend mode зафиксирован честно: текущий MVP — Web Service; Static Site остаётся отдельной задачей/refactor, а не скрытым допущением.
- [ ] Env contract перечисляет backend/frontend/worker переменные, включая auth, queue, payments, email, LLM и storage.
- [ ] В Story явно записано, почему `next.config.ts` rewrites и `/api/v1/...` fetch contract блокируют pure static deploy прямо сейчас.
- [ ] Есть post-deploy smoke checklist для backend/frontend/worker, включая OAuth/cookie-auth и enqueue задач.
- [ ] Story не обещает, что Render сам решает storage-проблему; зависимость на object storage делегирована в S09.

## Примечания

- Самый короткий MVP путь сейчас: все три приложения крутятся как управляемые сервисы на Render, а не пытаться насильно сделать frontend static первым шагом.
- `backend/Dockerfile` и `frontend/Dockerfile` сейчас dev-ориентированы (`uvicorn --reload`, `npm run dev`), поэтому Render-ready конфигурация почти наверняка потребует отдельные production команды или multi-stage build.
- Если продукт всё-таки хочет `frontend static`, это уже не настройка Render, а frontend refactor: убрать runtime rewrite-зависимость, ввести явный публичный API origin и перепроверить cookie/OAuth/CORS flow end-to-end.
- Для реального rollout удобнее сразу готовить `render.yaml`, но текущая Story фиксирует сначала deploy contract и список технических blockers, чтобы не обещать неверный static-hosting path.
