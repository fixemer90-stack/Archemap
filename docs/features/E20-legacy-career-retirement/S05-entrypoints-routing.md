# S05: Очистить UI entrypoints и deep-link routing

## Статус

🟢 Local acceptance verified: SPEC и code/security PASS (`deleg_fe8fe02d`, `deleg_4751131c`), 54 native browser tests PASS. Publication/CI и stage/production — отдельные gates S07; backend P1 не закрыт этим frontend verdict.

## Контекст

Отсутствие старой ссылки в sidebar не доказывает отсутствие legacy route. Клиент должен различать новый Career flow, существующий архив и отсутствие legacy row.

## Что сделать

1. Проверить sidebar, dashboard, adjacent CTAs и billing links: все новые Career entrypoints ведут в `/products/career`.
2. Старый `/report/{profileId}?product=career` не должен вызывать generation.
3. При существующем legacy row показать read-only archive и CTA в новый Career.
4. При отсутствии row направить/предложить переход в `/products/career`, сохранив допустимый `profileId` context.
5. Не смешивать generic report DTO с target Career DTO.
6. Покрыть browser tests для обоих deep-link сценариев и PDF download.

## Файлы

| Файл                                                       | Действие                           |
| ---------------------------------------------------------- | ---------------------------------- |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Archive/no-row behavior            |
| `frontend/src/app/(dashboard)/products/career/*`           | Target entrypoint                  |
| `frontend/src/lib/api/report.ts`                           | Legacy reads only; no Career write |
| Navigation/CTA components                                  | Route audit                        |
| `frontend/tests/e2e/*`                                     | Browser regressions                |

## Критерии приёмки

- [x] Все активные Career links ведут в target flow.
- [x] Existing legacy deep link отображает сохранённый отчёт и скачивает PDF.
- [x] Missing legacy row не вызывает `/reports/generate`.
- [x] Missing legacy row предлагает target Career с корректным profile context.
- [x] UI явно отличает архивный отчёт от нового Career Report.
- [x] Mobile/desktop browser tests подтверждают routing и ownership-safe errors.

## Evidence и границы

SPEC review `deleg_fe8fe02d`: PASS по source/coverage; независимо выполнены четыре lightweight contracts и discovery 54 browser cases. Reviewer не запускал браузер/build. Parent после copy-only banner delta выполнил все **54** Chromium cases на 1440/820/390, включая saved prose/native PDF wiring, no writes/poll/retry, mixed-profile/product rejection, 401/402/404 sanitization, stale Self fencing и обычный Self generation/poll/retry. Parent frontend lint/types/build и 16 contract scripts — PASS. Actual backend PDF bytes и persisted immutability подтверждены отдельно PostgreSQL integration suite, а не browser mock. Code/security `deleg_4751131c` — strict JSON PASS с проверенными code-only fingerprints; это не approval backend runtime и не production acceptance.
