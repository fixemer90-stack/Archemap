# E21.S07: Исправить графики расчётного слоя отчёта

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** 🟡 Production deployed; staging был явно пропущен для этого frontend-only hotfix

## Контекст

После production rollout E21 обнаружен дефект расчётного слоя V2-отчёта: данные рассчитаны и присутствуют в DOM, но часть полос и столбцов визуально прозрачна, подписи процентов не соответствуют ширине, а композиция растягивает компактные графики до высоты больших таблиц.

Контрольный production-артефакт: `/report/v2/548049cd-99d3-4186-ae5b-fc53a64b05e7`. Персональные данные владельца не входят в evidence и не должны копироваться в документацию или fixtures.

S04 зафиксировала миграцию report/chart компонентов на semantic tokens, но существовавшие visual gates не проверяли вычисленное CSS-свойство заливки, соответствие подписи ширине и содержательную полноту aspect network. Эта Story закрывает обнаруженный product/design defect, не изменяя расчёты и сохранённые отчёты.

## Подтверждённые причины

1. `bg-[var(--hero-background)]` компилируется Tailwind как `background-color: var(--hero-background)`, но `--hero-background` содержит gradient. Браузер отклоняет значение, и заливка остаётся прозрачной.
2. `percentWidth()` нормализует доли `0..1` в проценты, а подпись использует исходное значение через `formatValue()`: ширина `50%` отображается как `0.50%`.
3. `min-h-[28px]` не позволяет нулевому акценту дома выглядеть как нулевое значение.
4. `flex` + `h-full` растягивают короткий balance-блок до высоты таблицы планет; `min-h-[600px]` создаёт лишнее пустое пространство в house/aspect cards.
5. Aspect network сначала ограничивает узлы и рёбра через независимые `.slice()`, поэтому схема не обязана соответствовать таблице ключевых аспектов.
6. Расчётный слой смешивает русские и английские подписи (`Aquarius`, `North Node`, `orb`) и показывает длинную техническую таблицу без progressive disclosure.

## Что сделать

1. Добавить отдельные semantic chart-fill tokens для track, bar start/end, node, resource и tension в light/dark themes.
2. Использовать валидное `background`/`background-image` для gradients; не передавать gradient token в `background-color` utility.
3. Ввести единую нормализацию процентов, используемую и шириной/высотой, и пользовательской подписью.
4. Отделить подпись номера дома от столбца и разрешить строго нулевую высоту для нулевого значения.
5. Убрать принудительное выравнивание компактных графиков по высоте больших таблиц и пересобрать расчётный слой без dashboard-like пустот.
6. Формировать aspect network из одной детерминированной выборки наиболее точных/сильных аспектов; узлы должны выводиться из выбранных рёбер.
7. Использовать ту же выборку для графика и компактной таблицы; остальные аспекты раскрывать по явному действию пользователя.
8. Добавить легенду resource/tension и доступные полные названия узлов для hover, keyboard focus и screen reader.
9. Локализовать названия знаков, точек и терминов расчётного слоя.
10. Добавить отдельные ready fixtures с непустыми расчётными данными и browser assertions до обновления snapshots.

## Затрагиваемые файлы

| Файл/каталог                                                          | Действие                                       |
| --------------------------------------------------------------------- | ---------------------------------------------- |
| `frontend/src/app/globals.css`                                        | Semantic chart-fill tokens                     |
| `frontend/src/components/astrotype-v2/report/format.ts`               | Единая percent normalization                   |
| `frontend/src/components/astrotype-v2/report/V2BalanceBars.tsx`       | Видимые полосы и корректные labels             |
| `frontend/src/components/astrotype-v2/report/V2HouseEmphasis.tsx`     | Честная нулевая высота и читаемые акценты      |
| `frontend/src/components/astrotype-v2/report/V2AspectNetwork.tsx`     | Детерминированная сеть и легенда               |
| `frontend/src/components/astrotype-v2/report/V2KeyAspectsTable.tsx`   | Компактная выборка и progressive disclosure    |
| `frontend/src/components/astrotype-v2/report/V2CalculationLayer.tsx`  | Композиция без принудительных пустот           |
| `frontend/src/components/astrotype-v2/report/V2CalculationMatrix.tsx` | Валидные fills и локализованные labels         |
| `frontend/src/lib/astrotype-v2/report-view-model.ts`                  | Общая presentation selection при необходимости |
| `frontend/scripts/check-report-ux.mjs`                                | Source contracts дефекта                       |
| `frontend/tests/e2e/theme-visual.spec.ts`                             | Расчётный ready fixture и screenshots          |
| `frontend/tests/e2e/theme-accessibility.spec.ts`                      | Contrast, keyboard, overflow                   |

## Критерии приёмки

- [x] Ни одна chart fill не имеет вычисленное прозрачное значение при ненулевых данных в light и dark themes.
- [x] Значение, визуальная длина полосы и подпись используют одну нормализацию (`0.5` → `50%`).
- [x] Нулевой акцент дома имеет нулевую высоту; номер дома остаётся читаемым независимо от столбца.
- [x] Balance, house emphasis и aspect network не содержат искусственного пустого пространства из-за соседней таблицы.
- [x] Aspect network и компактная таблица строятся из одной детерминированной выборки.
- [x] Цвет, толщина и тип связи имеют текстовую/структурную альтернативу; добавлена понятная легенда.
- [x] По умолчанию не выводится необработанная таблица всех аспектов; полный список доступен через progressive disclosure.
- [x] В расчётном слое нет пользовательских подписей `Aquarius`, `Sagittarius`, `North Node`, `orb` и других необъяснённых английских терминов.
- [x] Ready fixture содержит непустые balance, house, network и matrix данные; тест падает на прозрачной заливке и неправильных процентах.
- [x] Visual matrix пройдена без snapshot update, после отдельного осознанного обновления baseline.
- [x] Light/dark screenshots проверены на 390, 820 и 1440 px; нет clipping и horizontal overflow.
- [ ] Исправление выложено сначала на staging и проверено на контрольном профиле без изменения persisted report/chart rows.
- [x] Production rollout выполнен exact green SHA; backup/rollback frontend image и marker проверены.

## Не входит в Story

- Изменение астрологических формул, весов, орбов или backend deterministic payload.
- Перегенерация или мутация уже сохранённых V2-отчётов.
- Изменение narrative sections и LLM prompts.
- Добавление новых астрологических показателей сверх уже рассчитанных данных.

## Baseline evidence

- Production SHA: `5da4407ee8334a784c7a1cbfa0da648595ebb0b0`.
- Контрольный route возвращает `200`; горизонтального overflow нет (`bodyWidth = viewportWidth = 1440`).
- В DOM присутствуют ненулевые значения: balance `50/33.3/16.7%`, house emphasis `100/50/25%`, matrix `71/29%` и `64/36%`.
- Вычисленная заливка элементов с inline width/height остаётся прозрачной.
- Production CSS содержит `.bg-[var(--hero-background)] { background-color: var(--hero-background) }`, тогда как token является gradient.
- Balance label показывает `0.50%` при inline width `50%`.
- Planet table имеет высоту около `1042 px`; соседний balance card принудительно растянут до той же высоты.
- Aspect table содержит 26 строк, а network ограничен 12 узлами и 16 рёбрами независимыми срезами.

## Проверка

```bash
cd frontend
npm test
npx eslint .
npx prettier --check .
npx tsc --noEmit --pretty false
npm run build
npx playwright test tests/e2e/theme.spec.ts
npx playwright test tests/e2e/theme-visual.spec.ts
npx playwright test tests/e2e/theme-accessibility.spec.ts
```

После генерации новых visual baselines тот же `theme-visual.spec.ts` обязательно запускается повторно без `--update-snapshots`.

## Evidence реализации

- RED зафиксирован source-contract проверками: до реализации `check-v2-report-view-model.mjs` падал на отсутствии общей presentation selection, а `check-v2-report-reader-dom.mjs` — на отсутствии chart tokens, legend и accessibility markers.
- Добавлены light/dark semantic tokens `--chart-fill-*`; bar/column fills используют валидный `background-image`, SVG network — отдельные node/resource/tension tokens.
- Ready fixture содержит дробные balance-значения, нулевой дом, resource/tension network, десять аспектов и непустую calculation matrix. Browser assertions проверяют computed fill, геометрию `0.5 → 50%`, нулевую высоту, общую выборку network/table, закрытый disclosure и локализацию.
- Visual baselines осознанно обновлены для V2 report в light/dark на 390, 820 и 1440 px; повторный запуск без `--update-snapshots`: `6 passed`.
- Финальная browser matrix: `theme.spec.ts` + `theme-visual.spec.ts` + `theme-accessibility.spec.ts` — `18 passed`; accessibility matrix отдельно проверяет keyboard focus узлов и отсутствие page-level horizontal overflow.
- `npm test`, `npx eslint .`, `npx prettier --check .`, `npx tsc --noEmit --pretty false` и `npm run build` прошли. ESLint сохранил две существующие warning в auth-страницах, ошибок нет.
- Persisted report/chart rows и backend deterministic payload не изменялись.

## Production rollout — 13 октября 2026 года

- По явному решению владельца frontend-only hotfix продвинут напрямую в production без staging. Поэтому staging-first критерий остаётся открытым как зафиксированное отклонение от обычного rollout-порядка.
- Runtime SHA и production marker: `9a7ca747fdd5acd26aab19de9e8a5bd83324a727`; CI run `38458157649` и Build & Push Images run `38458157683` завершились успешно до rollout.
- Scope выведен из production marker `5da4407ee8334a784c7a1cbfa0da648595ebb0b0`: между marker и target были только S07 frontend/tests/docs изменения, без backend-кода и миграций. Пересобран и пересоздан только `frontend`.
- Rollback anchor: image `sha256:8df5c9c5966d461dceedd0da2c950db89eec6c59054dd6565b595e1e0d2ed132`, tag `astrotype-frontend:rollback-5da4407`; предыдущий frontend source archive сохранён с SHA-256 `d686782257d2d39ffd9a98397ace060242f149b44e0eec6ebf3688bbc59225b9`.
- Новый frontend image: `sha256:23355095454cb7c1263b58993a9fe0c53baa161118875c25789b6dfabaa03be8`; compiled bundle содержит `chart-fill-bar-start` и `Показать все аспекты`.
- Production `health`, `/` и контрольный `/report/v2/548049cd-99d3-4186-ae5b-fc53a64b05e7` вернули HTTP `200`; все Compose services находятся в running state, frontend logs после rollout не содержат error/fatal/exception.
- До/после rollout совпали counts и ID hashes: natal charts `14|e56db3cf0d5516b70d96fae9bdb75608`, natal reports `16|68c40f9905d41a1b1efec10b3f29d609`.
- Evidence: `/opt/astrotype/backups/production/deploy-9a7ca747fdd5acd26aab19de9e8a5bd83324a727-20261013T204507Z`.
- Из-за ограниченной RAM сборка потребовала временный swap `4 GiB`; после успешного rollout swap удалён, health и frontend image повторно прочитаны.
