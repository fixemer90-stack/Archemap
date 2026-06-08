# Story E8.S09: Artifact Storage Strategy for Render / S3 Replacement

**Feature:** [Production & Scale](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Render закрывает web services, background workers, managed Postgres и managed Redis/Valkey, но не закрывает хранение PDF/report artifacts сам по себе.

Текущий backend уже жёстко завязан на S3-compatible storage:
- `backend/app/modules/reports/storage.py` создаёт `boto3` client и работает только через `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `S3_REGION`;
- `backend/app/modules/reports/tasks.py` после генерации PDF всегда делает `await storage.upload(...)` и затем `storage.get_signed_url(...)`;
- helper `ensure_bucket()` существует, но по текущему коду нигде не вызывается автоматически, значит bucket bootstrap пока остаётся внешним операционным шагом.

Это создаёт реальный deployment gap:
- локальный `minio` из `docker-compose.yml` не существует на Render;
- хранение PDF на локальном filesystem Render нельзя считать рабочей заменой: файловая система эфемерна, web и worker разделены, signed URL contract пропадает;
- попытка "просто выключить S3" ломает deliverable path отчётов, где `pdf_generated` и `pdf_url` ожидают настоящий artifact backend.

## Что сделать

1. Принять и зафиксировать MVP-решение по storage:
   - preferred path: сохранить S3-compatible contract и подключить внешний provider;
   - alternative path: отдельный refactor stories, если продукт хочет уйти от S3-интерфейса полностью.
2. Для preferred path описать допустимых провайдеров и критерии выбора:
   - Cloudflare R2;
   - Backblaze B2 S3-compatible;
   - Yandex Object Storage;
   - любой другой provider с S3 API и presigned URL support.
3. Зафиксировать, что для Render MVP не подходит как "решение":
   - локальный диск внутри web service;
   - локальный диск внутри worker;
   - Render persistent disk как общий artifact store между web и worker без отдельного application refactor;
   - хранение PDF только в Postgres как быстрый инфраструктурный workaround.
4. Описать bootstrap contract:
   - bucket/container должен существовать до первого `reports.generate_pdf`;
   - если автосоздание bucket не добавлено в runtime path, это должен быть явный deploy step/operator checklist item;
   - smoke check обязан проверять upload и получение signed URL, а не только успешную генерацию report row в БД.
5. Если команда выбирает replacement instead of workaround, выделить отдельный engineering scope:
   - abstraction layer поверх `S3Storage`;
   - новый storage backend contract;
   - миграция `pdf_url`/artifact delivery semantics;
   - обновление runbooks, tests и Render deploy docs.
6. Синхронизировать решение с E8 S08 и E12 runtime docs, чтобы deployment contract и локальный runbook не расходились.

## Рекомендуемое решение

Для первого deploy на Render рекомендован не storage replacement, а storage carry-over:

- оставить текущий S3-compatible application contract без изменений;
- вместо локального MinIO подключить внешний managed/object-storage provider;
- первыми кандидатами считать Cloudflare R2 или Yandex Object Storage, потому что они сохраняют presigned URL workflow без application refactor.

Иными словами, проблему с S3 сейчас лучше не «обходить» локальным диском Render, а вынести наружу в совместимый object storage. Полная замена S3-интерфейса допустима, но только как отдельный engineering track после первого рабочего managed deploy.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/reports/storage.py` | Текущий S3-only artifact backend |
| `backend/app/modules/reports/tasks.py` | PDF upload + signed URL path |
| `docker-compose.yml` | Локальный MinIO baseline, отсутствующий на Render |
| `docs/features/E8-production-scale/S08-render-deploy.md` | Render deploy contract, который зависит от storage decision |
| `docs/features/E12-llm-report-runtime-readiness/S04-object-storage-pdf-bootstrap.md` | Runtime/bootstrap story, которую нужно держать синхронной с deployment решением |
| `docs/SRS/SRS-E8-production-scale.md` | Инфраструктурный контракт на уровне требований |

## Acceptance Criteria

- [ ] В документации есть явное решение: для Render MVP используется внешний S3-compatible provider, либо создан отдельный refactor-track на замену storage backend.
- [ ] Задокументировано, почему локальный filesystem Render не может считаться рабочей заменой для PDF/report artifacts.
- [ ] Перечислен обязательный env contract для external object storage: endpoint, bucket, credentials, region.
- [ ] Явно отмечено, что `ensure_bucket()` сейчас не является подтверждённым runtime bootstrap path и bucket existence нельзя считать автоматической.
- [ ] Есть bootstrap/smoke checklist: bucket exists -> upload succeeds -> signed URL opens artifact.
- [ ] Если выбран полный отказ от S3, документация фиксирует это как отдельную инженерную задачу, а не как незаметную настройку Render.
- [ ] S08 Render deploy и E8 SRS не расходятся с принятым storage decision.

## Примечания

- Самый быстрый путь к первому деплою на Render — не заменять storage layer, а оставить S3-compatible contract и подключить внешний provider.
- Полноценная замена S3 — это уже не infra-tweak, а изменение application contract: `reports/tasks.py`, signed URLs, bootstrap, smoke checks и, возможно, API ожиданий frontend.
- Если продукту важен именно отказ от внешнего object storage, это лучше делать отдельной серией stories после первого рабочего managed deploy, а не смешивать с первичным Render rollout.
- Render persistent disk не закрывает текущий контракт артефактов: worker и web service разделены, а код ожидает единый object store с upload + signed URL semantics.
