# Astrotype Patch Log

Append-only журнал изменений, фактически доставленных в production. Он дополняет Git-историю и feature-документацию: фиксирует границы релиза, миграции, feature flags, backup/rollback anchor и проверенный runtime-результат.

## Правила ведения

- Новые записи добавляются сверху, сразу после этого раздела.
- Одна запись соответствует одному production rollout или hotfix.
- Указывается точный полный Git SHA, а не только название ветки.
- Запись описывает только реально применённые изменения; планы и staging-only работу сюда не добавляем.
- Для изменений схемы обязательны revision БД и проверенный backup.
- Статус `deployed` ставится только после readback production marker, health и профильных smoke-проверок.
- Документационный коммит, добавляющий запись, не меняет SHA уже развёрнутого runtime.

## Шаблон

```markdown
## YYYY-MM-DD · `<short-sha>` · Короткое название

- **Статус:** deployed | rolled back | partial
- **Окно:** `<started UTC>` → `<verified UTC>`
- **Runtime SHA:** `<full sha>`
- **Предыдущий SHA:** `<full sha>`
- **База:** `<revision before>` → `<revision after>` или `без миграций`
- **Feature flags:** только изменённые значения
- **Backup:** путь, размер и SHA-256 или `не требовался`

### Добавлено

- ...

### Изменено / исправлено

- ...

### Проверено

- ...

### Rollback

- ...
```

---

## 2026-10-13 · `9a7ca74` · Графики расчётного слоя V2-отчёта

- **Статус:** deployed
- **Окно:** `2026-10-13T20:45:07Z` → `2026-10-13T20:55:43Z`
- **Runtime SHA:** `9a7ca747fdd5acd26aab19de9e8a5bd83324a727`
- **Предыдущий SHA:** `5da4407ee8334a784c7a1cbfa0da648595ebb0b0`
- **База:** без миграций; revision осталась `f1a2b3c4d5e6`
- **Feature flags:** без изменений
- **Backup:** rollback image `sha256:8df5c9c5966d461dceedd0da2c950db89eec6c59054dd6565b595e1e0d2ed132` (`astrotype-frontend:rollback-5da4407`) и frontend source archive SHA-256 `d686782257d2d39ffd9a98397ace060242f149b44e0eec6ebf3688bbc59225b9`

### Изменено / исправлено

- Исправлены прозрачные chart fills, единая нормализация процентов и нулевая высота пустых house bars.
- Aspect network и компактная таблица переведены на общую детерминированную выборку; добавлены legend, accessibility alternatives и progressive disclosure.
- Убрано принудительное растягивание расчётных карточек; пользовательские astro labels локализованы.

### Проверено

- Exact-SHA CI run `38458157649` и Build & Push Images run `38458157683` завершились успешно.
- Production marker прочитан как runtime SHA; scope — `release:frontend-only`.
- Новый frontend image `sha256:23355095454cb7c1263b58993a9fe0c53baa161118875c25789b6dfabaa03be8` запущен; compiled bundle содержит chart/disclosure markers.
- `health`, `/` и контрольный V2 report route вернули HTTP `200`; все Compose services работают, новых frontend errors нет.
- V2 natal chart/report counts и ID hashes до/после совпали; backend и PostgreSQL не пересоздавались.
- Временный deploy swap удалён после сборки; post-cleanup health остался green.

### Rollback

- Перетегировать `astrotype-frontend:rollback-5da4407` как `astrotype-frontend:latest`, восстановить предыдущий frontend source archive и пересоздать только service `frontend`.
- Evidence: `/opt/astrotype/backups/production/deploy-9a7ca747fdd5acd26aab19de9e8a5bd83324a727-20261013T204507Z`.

---

## 2026-10-10 · `f958e0d` · Billing, birth-data refinement и responsive navigation

- **Статус:** deployed
- **Окно:** `2026-10-10T08:13:38Z` → `2026-10-10T08:24:04Z`
- **Runtime SHA:** `f958e0d600216a5949605e65dd6c2e97fd9f5e93`
- **Предыдущий SHA:** `d87dfc8d1d2d14e04d171262f2b00a9d0f9b591a`
- **База:** `d9e0f1a2b3c4` → `f1a2b3c4d5e6`
- **Feature flags:** `BIRTH_DATA_REFINEMENT_ENABLED=true`, `NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED=true`
- **Backup:** `/opt/astrotype/backups/production/deploy-f958e0d600216a5949605e65dd6c2e97fd9f5e93-20261010T081338Z/database.dump`, `1,671,420` bytes, SHA-256 `caf83e561c755de7840e5fc843cf075bbf1c40659a4bf72a87a66a3525fe2887`

### Добавлено

- Месячная модель Plus-подписок, периоды доступа, renewal lifecycle, отмена и возобновление подписки.
- Billing UI для статуса Plus и управления подпиской.
- Production workflow уточнения времени и места рождения с отдельным monitor worker.
- Адаптивная навигация: desktop sidebar `280 → 76 px`, tablet rail и mobile drawer до `336 px`.
- Индексы мониторинга birth-data refinement и таблицы subscription-модели.

### Изменено / исправлено

- Неактивный raw payment status удалён из пользовательского billing UI.
- Незавершённая светлая тема отключена; production остаётся в проверенной тёмной теме.
- Backend Docker base закреплён на `python:3.12-slim-bookworm`, чтобы сборка не зависела от изменений плавающего `python:3.12-slim`.
- Refinement monitor изолирован в singleton queue/worker без prefork и с конфигурируемыми порогами.

### Проверено

- Production marker совпадает с runtime SHA.
- Backend, frontend, worker, scheduler, refinement-monitor, PostgreSQL и Redis запущены; health API вернул `200` и `status=ok`.
- CI для точного SHA: backend/frontend lint, tests, contracts, security audit и Docker build — success.
- Protected-table counts до и после миграции совпали; backup восстановлен в disposable database до rollout.
- Новые subscription/refinement маршруты присутствуют в live OpenAPI; unauthenticated payment и billing boundaries возвращают `401`.
- Refinement monitor выполнил задачу успешно; незарегистрированных Celery-задач и traceback нет.
- Live production UI проверен на `1440×900` и `390×844`: sidebar/drawer работают без горизонтального overflow.

### Rollback

- Исходный runtime marker: `d87dfc8d1d2d14e04d171262f2b00a9d0f9b591a`.
- Сохранены source snapshot, `.env.production` до rollout и проверенный PostgreSQL backup в каталоге evidence.
- Миграции добавляют индексы и subscription-таблицы; откат приложения без восстановления БД допустим только после проверки совместимости старого runtime со схемой `f1a2b3c4d5e6`.
