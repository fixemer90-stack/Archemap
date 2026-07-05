# E15 — Self Report Human Storytelling

> Статус: ⬜ Не начато
> Дата подготовки: 2026-07-02
> Источник: пользовательский фидбек по живому Self report `/report/877508cc-3e32-4fab-ab64-a939afc01fac`: “отчёт очень плох по сторитейлингу и скуповат”, нужно сделать “менее душным, чуть более человечным”.
> Зависимости: E11 ✅, E12 ✅, E13 ✅, E14 ✅

## Цель

Сделать Self report менее сухим и более человеческим без потери доказательности: отчёт должен читаться как живой психологический портрет, а не как аккуратная справка по карте или JSON-rendered summary.

E15 не добавляет “ещё больше блоков” ради объёма. Он меняет качество повествования: больше узнавания, конкретных жизненных проявлений, плавных переходов, человеческого языка и драматургии внутри уже существующего staged narrative pipeline.

## Проблема

После E13/E14 отчёт технически стал богаче: есть `DeepNatalSynthesis`, staged prompts, evidence refs, домовые сценарии, противоречия, maturity levels и PDF parity. Но живой пример показывает другой дефект качества:

- текст звучит слишком “служебно”: “формирует паттерн”, “эмоциональная обработка”, “динамика”, “механизм”;
- hero начинает с фактов карты вместо момента узнавания;
- секции выглядят как сжатая аналитическая сводка, а не как история о человеке;
- assembler часто берёт один параграф из stage output и сжимает материал;
- сторителлинг боится быть живым, потому что evidence/safety guardrails сильнее tone guidance;
- отчёт корректен, но не вызывает ощущения “меня поняли”.

## Product direction

Целевой Self report должен оставаться evidence-backed, но в пользовательском слое звучать так:

```text
узнавание → личная формула → жизненная сцена → внутреннее напряжение → защитная стратегия → зрелая форма → мягкий вопрос
```

А не так:

```text
факт карты → технический вывод → следующий факт карты → ещё один вывод
```

## Принципы

1. Человечность без эзотерической воды. Текст должен быть живым, но не расплывчатым.
2. Evidence остаётся источником истины, но не обязан звучать в каждом первом абзаце.
3. Сначала смысл и узнавание, потом основания.
4. Один хороший жизненный сценарий ценнее трёх абстрактных claim-ов.
5. Self не превращается в терапию, диагноз, Love или Career.
6. Не “больше текста”, а больше плотности и дыхания: конкретика, переходы, ритм, меньше канцелярита.
7. Технические блоки и evidence должны поддерживать доверие, но не ломать чтение.

## Scope

### In scope

- Новый tone/storytelling contract для staged Self prompts.
- Prompt family v2 для humanized section generation.
- Правила для hero: меньше технического старта, больше recognition-first входа.
- Изменения deterministic assembler, чтобы не сжимать stage outputs до одного сухого параграфа.
- Автоматические quality gates против “душного” языка и канцелярита.
- Проверка плотности: каждая ключевая секция содержит жизненное проявление, риск/защиту и зрелую форму.
- Frontend/PDF rendering без превращения новых текстов в простыню.
- Runtime A/B smoke на живом Self report: до/после по конкретному профилю.

### Out of scope

- Пересчёт натальной карты, соционики или правил архетипов.
- Новые платные вертикали.
- Полный Career/Love-разбор внутри Self.
- Диагностический/терапевтический язык.
- Ручной one-off текст, который не проходит через общий pipeline.
- Удаление evidence/validators ради “красивого текста”.

## Target report feel

### До

> Солнце и Луна в Козероге в 7 доме формируют устойчивый паттерн самоопределения через партнёрство и диалог.

### После

> Вам важно не просто “быть собой” в вакууме — вы как будто точнее собираетесь рядом с другим человеком. В диалоге быстрее становится понятно, где ваша позиция, за что вы отвечаете и насколько отношения выдерживают реальность, а не только эмоцию момента.

Разница: второй вариант не выдумывает новые факты, но начинает с человеческого переживания, а факт карты может быть раскрыт ниже в evidence.

## Stories

| Story | Название                                   | Статус       | Документ                                 |
| ----- | ------------------------------------------ | ------------ | ---------------------------------------- |
| S01   | Human storytelling contract and tone guide | ✅ Готово    | `S01-human-storytelling-contract.md`     |
| S02   | Staged prompt family v2                    | ✅ Готово    | `S02-staged-prompts-v2.md`               |
| S03   | Assembler expansion and narrative rhythm   | ✅ Готово    | `S03-assembler-narrative-rhythm.md`      |
| S04   | Humanized quality gates                    | ✅ Готово    | `S04-humanized-quality-gates.md`         |
| S05   | Frontend/PDF readability and pacing        | ⬜ Не начато | `S05-frontend-pdf-readability.md`        |
| S06   | Live before/after smoke and rollout        | ⬜ Не начато | `S06-live-before-after-smoke-rollout.md` |

## Acceptance criteria

- [ ] Hero opens with recognition-first prose, not raw placements or typology labels.
- [ ] Every key Self section includes at least one concrete lived manifestation.
- [ ] Key sections follow the chain: meaning → scenario → tension/risk → mature expression.
- [ ] Stage prompts explicitly ban канцелярит and overused abstract markers unless grounded in concrete behavior.
- [x] Assembler preserves enough stage prose to avoid one-paragraph compression while still keeping sections readable.
- [x] Validators/quality gates detect generic horoscope prose and “служебный” tone markers.
- [ ] Evidence notes remain present but secondary/collapsed in UI and PDF.
- [ ] Frontend/PDF render longer narrative with rhythm: paragraphs, emphasis, collapsible support blocks, no wall of text.
- [ ] Fresh live Self report regeneration for the reference profile produces a visibly more human report and still reaches `report.status=ready`, `narrative.status=ready`, PDF `200`.
- [ ] Backend and frontend regression gates pass.

## Implementation order

1. Define the human storytelling contract and examples (`S01`).
2. Create v2 staged prompts and prompt tests (`S02`).
3. Update assembler composition rules (`S03`).
4. Add tone/readability quality gates (`S04`).
5. Adjust frontend/PDF rendering if needed for longer human prose (`S05`).
6. Run before/after smoke on the reference report and document rollout policy (`S06`).

## Verification plan

Backend targeted:

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives -q'
docker compose exec -T backend sh -lc 'cd /app && python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives && python -m ruff format --check app/modules/report_narratives tests/unit/test_report_narratives'
docker compose exec -T backend sh -lc 'cd /app && python -m mypy app/modules/report_narratives'
```

Frontend targeted:

```bash
cd frontend
node scripts/check-report-ux.mjs
npx tsc --noEmit --pretty false
npx prettier --check src/components/report src/lib/report scripts/check-report-ux.mjs
```

Runtime smoke:

```bash
docker compose ps
curl http://localhost:8000/api/v1/health
# login -> POST /api/v1/reports/{id}/narrative/regenerate -> poll GET /api/v1/reports/{id}
# verify narrative.ready, inspect web report, verify PDF 200
```

## Relationship to E13/E14

E13 answered: what deeper semantic blocks the report must understand.

E14 answered: how the staged pipeline reliably generates those blocks.

E15 answers: how those blocks should sound and read so the product feels human rather than dutifully correct.
