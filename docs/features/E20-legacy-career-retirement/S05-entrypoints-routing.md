# S05: Очистить UI entrypoints и deep-link routing

## Статус

⬜ Не начато

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

- [ ] Все активные Career links ведут в target flow.
- [ ] Existing legacy deep link отображает сохранённый отчёт и скачивает PDF.
- [ ] Missing legacy row не вызывает `/reports/generate`.
- [ ] Missing legacy row предлагает target Career с корректным profile context.
- [ ] UI явно отличает архивный отчёт от нового Career Report.
- [ ] Mobile/desktop browser tests подтверждают routing и ownership-safe errors.
