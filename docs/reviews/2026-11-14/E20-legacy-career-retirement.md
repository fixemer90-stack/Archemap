# E20: verification и независимые review gates

## Статус

Source SPEC/code-security gates пройдены, P1 `E20-CQ-01` исправлен и принят независимым re-review. Post-fix full persisted regression PASS; publication/CI и live acceptance остаются отдельными gates. Это не Feature completion, production census или rollout evidence. Родительский checkout: `/mnt/d/Python/Balthier/Archemap`, исходный implementation baseline `45c2521`.

## S01 — SPEC review `deleg_1c7aa62e`

Первый verdict: **BLOCKED**. Reviewer независимо исполнил 8 pure units, прочитал SQL и integration tests; PostgreSQL не запускал. Parent DB evidence не выдаётся за независимый запуск reviewer.

Findings:

- [x] Falsy root metadata: census не считал `[]`, хотя canonical `EntitlementsService.has_active_direct_product_access` считает такой active grant прямым. Исправлен SQL predicate для всех database-representable falsy JSON roots, не меняя authorization runtime. Добавлена параметризованная real-PostgreSQL regression matrix (`[]`, `false`, `0`, пустая строка, `{}`, `null`) с вызовом настоящего canonical service. Зафиксирован RED **4 failed / 2 passed**; после изменения полный census suite **16 passed**. Сохранились исходные read-only/protected-output/nonempty-array cases.
- [x] Parent status: reviewer увидел старую таблицу Feature до parent update. Fresh readback подтверждает S01 **Source/tool verified; live blocked**, а не «Не начато» или complete. S01 и parent продолжают оставлять production census открытым.
- [x] Повторный SPEC verdict получен: **BLOCKED**, найден отдельный numeric-underflow counterexample (см. ниже).
- [x] SPEC PASS после numeric-underflow исправления получен (`deleg_fe8fe02d`, source review).
- [x] После SPEC PASS выполнено отдельное независимое code/security review S01/S05: `deleg_4751131c`, strict JSON PASS; fresh scoped fingerprints совпали.

Проверки parent после исправления: Ruff/format/scoped mypy — PASS; 8 unit + 8 real PostgreSQL integration = **16 passed**. Owned disposable PostgreSQL удалён и отсутствие проверено. Production/restored snapshot не доступен; synthetic counts не переносятся в production evidence.

## S01 — SPEC re-review `deleg_30a16bef`

Verdict: **BLOCKED** по новому underflow edge; оба исходных finding закрыты. Reviewer подтвердил canonical authorization для raw JSON `1e-400` / `-1e-400`: configured decoder превращает их в falsy Python floats, тогда как SQL `jsonb` сохранял точное ненулевое число. Reviewer не запускал PostgreSQL, оба scoped unit rerun завершились timeout; это не independent PASS.

- [x] Raw numeric underflow устранён в SQL classification без изменения application authorization. `direct_marker` выбирает root либо `subscription_id` для object; number classifier использует точную binary64 half-minimum границу `2^-1075`, вычисленную через PostgreSQL `numeric` как `5^1075 * 10^-1075`. Не используется float cast с отдельным PostgreSQL underflow behavior.
- [x] Добавлены **18** real-PostgreSQL raw-literal cases: обе позиции, знаки, underflow, точная tie-to-even граница и значения по обе стороны, nonzero subnormals, нормальный tiny float и nested overflow. Raw JSON вставляется до decoding; actual `metadata_json` читается через настроенный SQLAlchemy/asyncpg decoder и передаётся реальному canonical service. Boundary test literals независимо вычислены через Python Decimal.
- [x] RED: **12 failed / 6 passed**; после исправления полный census suite **34 passed** (**8 unit + 26 integration**). Исходные privacy/aggregate/immutability/read-only cases сохранены. Ruff/format/scoped mypy — PASS; собственный disposable container удалён с readback.
- [x] Новый независимый SPEC verdict по этому candidate получен: **PASS**, `deleg_fe8fe02d`.

При ошибке unsupported JSON→numeric conversion инструмент по-прежнему завершается nonzero без выдачи частичных counts; такое чтение нельзя принимать за пустой census. No production identity/counts или live compatibility usage не подтверждены.

## Возобновление после ограничения API

Оба SPEC reviewers в `deleg_58e01aee` остановились на **HTTP 429 / usage limit**; положительных или отрицательных verdict по текущему candidate они не выдали. Это не отказ пользователя и не падение тестов. Повторные независимые SPEC reviews запущены для census/frontend (`deleg_fe8fe02d`) и backend/contracts (`deleg_644a7521`). Code/security gate остаётся открытым до SPEC PASS.

## SPEC acceptance `deleg_fe8fe02d`

- **S01 source SPEC PASS**: previous falsy/underflow blockers resolved; explicit connection/read-only/repeatable-read/aggregate/error boundaries and honest live blockers accepted. Reviewer не запускал PostgreSQL или unit suite; interpreter/dependency probe timeout 20s не считается execution PASS.
- **S05 source SPEC PASS**: active entrypoints, read-only archive/missing/PDF wiring, ownership-safe errors, DTO separation, Self regression/stale fences accepted. Reviewer независимо выполнил четыре lightweight contract scripts, diff check и Playwright discovery **54** cases; browser/build не выполнял.
- Code/security review S01/S05 запущен отдельно (`deleg_14f628ba`), читает также parent copy-only delta. Backend SPEC принят отдельно ниже.

## Backend SPEC acceptance `deleg_644a7521`

**PASS** по S02/S03/S04 и runtime S06. Reviewer независимо выполнил **224** scoped units (20.50s) и ASGI/custom probe с mocked persistence и real PDF: шесть historical statuses, JSON и GET/HEAD/POST PDF, exact regeneration 410, no flush/commit/refresh, telemetry **6 JSON reads / 18 PDF requests**. Runtime/tracked OpenAPI parity принята. Исходный probe AsyncMock был исправлен в harness, не в продукте; конечный probe PASS.

Persisted DB reviewer не запускал; parent **230 passed** остаётся отдельным исполнением. Parent проверил fresh scoped tracked backend/contracts SHA256 `3ee99ed8262878c9275aa27fad433bafb3068375bd2b69dab95e984947222cfb` и **15-file** manifest (включая четыре untracked source/test files) `c3b453fdbbad60882d1dddffe654efceb911bcdd60f25163469fed5d23aeeaf0`: совпадают с review. Global fingerprint не используется для расширения scope на frontend copy delta.

После SPEC PASS отдельно запущен backend code/security review (`deleg_379c7ea6`). Parent added-line security scan: **2171** lines, только три credential-pattern matches в inert test fixtures (unused password, synthetic privacy marker, fake credential-redaction URL). Runtime secrets/shell execution/eval-exec/pickle/dynamic-SQL matches не найдены; текст credential values не выводился. Parent scoped scan findings были queued через steer, но completion подтвердил, что позднее сообщение не успело попасть reviewer; не считаются им полученными. Backend security verdict получен ниже и содержит независимо воспроизведённый P1.

## S01/S05 code/security `deleg_14f628ba`

Narrative verdict **PASS**, без actionable security/correctness/race/performance findings; проверены 18 scoped files и final copy-only delta. Reviewer независимо выполнил retirement contract script и scoped diff check. Browser/DB/integration/PDF execution не выполнялся, parent evidence не присвоен.

Strict JSON correction `deleg_4751131c`: **PASS**, security_concerns/logic_errors/suggestions пусты. Reviewer подтвердил все **12** code files и final banner delta, independently retirement script/diff check и scoped scan **1175** added lines: только два inert census fixture credential-pattern matches. Browser/DB/PDF execution не выполнялся. Parent fresh tracked diff и каждый из семи untracked file hashes совпали с возвращёнными fingerprints; approval принят только для S01/S05, не для backend P1.

Старый ответ был narrative, поэтому выполнен один bounded correction/reaffirmation с code-only scope. Docs metadata исключена из code approval. Verified fingerprints: tracked code diff `368b71fef1489e28fa6ba7db8350ff2fe1437844f40a904005f7607e3d2f4182`; seven-untracked-code manifest `86d1cc635bcb9bd1e7b857394827c06c5f60d8c27f5c5f4f21264464e10315b2`; complete **12-file code manifest** `eef47b9b84088a8bffe96e795399c2aaa83a19a7de85defd7a0914cdebdb0fe0`.

## Backend code/security `deleg_379c7ea6` — FAIL

### E20-CQ-01 — P1: path-shaped product retirement bypass

Status: **FIXED — independent SPEC + CODE/security re-review PASS**, third-context fix `deleg_0aa9757e`. Это code closure; full persisted QA, publication/CI и live acceptance не подразумеваются.

Root cause: exact `product == "career"` retirement guard передаёт остальные arbitrary strings в filesystem-based `load_ruleset`. Independent actual ASGI probes с mocked snapshot persistence, real feature extraction/rules/evaluation/rendering вернули HTTP **200** и Career claims для `career/.`, `career/`, `self/../career`; literal `career` вернул **410** до snapshot lookup. Отдельно 16 scoped tests были зелёными, но этого класса inputs не покрывали. Никакие DB/provider/remote операции reviewer не выполнял, sockets были заблокированы.

Fix acceptance:

- [x] Exact non-path canonical allowlist на HTTP и direct-service input boundaries до DB/chart/rules/mutation.
- [x] Malformed/unsupported identifiers отвергаются, не strip/lower/path-normalize; literal `career` остаётся parseable и даёт original structured 410.
- [x] HTTP/direct Rules и Report service regressions воспроизводят path aliases и no-work boundary; supported Self остаётся рабочим.
- [x] Tracked/runtime schema allowlist согласована.
- [x] Targeted/broader verification после последнего code edit PASS; fresh independent SPEC/code-security re-review закрывает P1. Full persisted QA учитывается отдельно в S07.

Parent contract tracer: добавлен exact enum assertion для обоих request schemas; RED **2 failed** на отсутствующем allowlist. После static enum `[self, love, child, career]` полный tracked-contract suite **8 passed**, Ruff/format/mypy и Redocly PASS.

Fix handoff: новый `app/core/products.py` задаёт общий Literal и exact membership validator; оба request DTO используют его, оба generation/interpretation service entrypoint вызывают validation до любых lookup/mutation/rules. Stored artifacts, queued handlers, access policy и pure rules loader не менялись. Third-context TDD: RED `career/.` дошёл до SQL assertion; GREEN matrix **101 passed**, author full units **1580 passed** (это author evidence, не parent rerun).

Parent fresh execution после handoff: **119 passed** (101 validation + 8 contracts + 10 retirement), Ruff/format **539 files** PASS, mypy **519 source files** PASS. Runtime и tracked enums проверены этими тестами. Parent post-fix full persisted integration suite на own PostgreSQL/Redis: **230 passed**, 3 warnings in **1385.19s**, test/cleanup exits 0; final task-label readback пуст. Fresh SPEC re-review `deleg_b016d85a` — PASS; CODE re-review `deleg_fdb0b999` — PASS после него; оба scoped approvals приняты. Frozen **18-file** backend/contracts manifest `01e77c442f6436f1ae2e10860831cba61f37659adcc2a39a13e06419588965f8`, tracked diff `9322392c19ef97866870cdabb4bcc94ec665305174304c94b03e7c549ac84bf1`.

### Post-fix independent SPEC `deleg_b016d85a` — PASS

Independently **316 unit tests passed** (1 HarfBuzz deprecation warning), затем real ASGI probe: **22 malformed requests → 422** и ноль snapshot/features/rules/SQL/mutation calls; оба literal Career endpoints → structured 410; real Self pipeline → 200 с **2 claims** при mocked snapshot. Шесть historical statuses сохранили payload/status/version/error без refresh/mutation; direct narrative generation → 410 без изменений. Pure Career loader и access/worker/telemetry invariants проверены. Persisted DB, browser, PDF и production execution этот reviewer не выполнял. Custom probe показал dotenv parse warnings; явные unreachable settings и socket denial не допустили внешнего доступа.

Parent сверил reviewer JSON-encoded fingerprints по всем current files: 18-file scope `5969b14ee953a7a173cee668464b632f04fc66b6dd251fe0e32fd6082832e169`, broader unchanged guard (21 files, включая три census) `3c16a3a1f4f71d9571623818330585e172af5db89912bcdbb95bfe20e4602e22`. Source не менялся между review и adoption.

Fresh parent static scan **1183 added lines**: один credential-assignment pattern — `hashed_password` inert fixture в `backend/tests/integration/test_e20_legacy_career_retirement.py:31`, не runtime secret; shell/eval/exec/pickle/dynamic-SQL matches отсутствуют.

### Post-fix independent CODE/security `deleg_fdb0b999` — PASS

Strict JSON `passed=true`, security/logic/suggestions пусты. Все **18** candidate files просмотрены; independently **119 tests passed** с real ASGI rejection/Career 410/real Self rules. Inert credential fixture классифицирован отдельно; scoped diff check PASS. Tests: unreachable DB/Redis/Celery, disabled/mock LLM, dotenv suppression и socket denial. Initial shell timeouts и inherited Python-path contamination устранены isolated interpreter mode; это harness issue, не product regression. Persisted DB/browser/production/full-unit execution reviewer не выполнял.

Parent повторно вычислил оба current 18-file fingerprints после verdict: JSON `5969b14ee953a7a173cee668464b632f04fc66b6dd251fe0e32fd6082832e169`, sorted SHA/path `01e77c442f6436f1ae2e10860831cba61f37659adcc2a39a13e06419588965f8`; совпадают с before/after reviewer. Approval принят для frozen source; parent post-fix full persisted integration затем прошёл **230 tests**, cleanup и readback PASS.

Прежние source SPEC PASS и parent **1477 unit / 230 integration** характеризуют candidate **до fix**, не доказательство отсутствия обхода и не разрешение публикации. Pure retained Career rules loader и historical reads не удаляются и не нормализуются при исправлении.

## Historical parent QA до P1 fix

На этом этапе авторские backend/frontend lanes были завершены без commits/push/deploy; ниже сохранён прежний baseline. Он не заменяет post-fix evidence выше. Parent тогда независимо подтвердил:

- Final full backend unit suite **1477 passed**, 5 warnings, exit 0; после additive static-schema sync targeted retirement+contract suite **16 passed** (6 contract + 10 retirement). JSON/Pydantic archive availability согласована, historical `report_data` остаётся свободным сохранённым object.
- Repo-wide backend Ruff/format — PASS (**537** files), mypy — PASS (**517** source files).
- OpenAPI Redocly — PASS, три существующих предупреждения (license metadata, localhost server, health без 4xx).
- Frontend **16** contract scripts, repo-wide ESLint (0 errors, 2 существующих auth-navigation warnings), Prettier, TypeScript и production build — PASS.
- Parent visual inspection выявил в новом архивном banner технические `Career v1` и raw `ready`/status. Copy-only delta убрал version/enum из banner без изменения fetch/auth/state logic и saved prose. Native browser RED: **1 failed** на новом заголовке; затем полный E20 Chromium suite на desktop/tablet/mobile — **54 passed**. Non-ready cases дополнительно запрещают raw-status label; original immutable prose и PDF/native CTA checks сохранены. Parent повторно осмотрел обновлённый mobile artifact.
- Full PostgreSQL/Redis integration suite: **230 passed**, 3 warnings, `integration_exit=0 cleanup_exit=0`. Использованы только отдельные owned disposable containers с explicit test URLs, mock/disabled LLM и пустыми payment credentials; команда удалила свои containers, final readback с task label пуст. Реальные archive PDF/immutability/access/worker/census regressions пройдены локально, не на stage/production.

Frontend SPEC завершился до copy-only delta; последующий S01/S05 code/security `deleg_4751131c` прочитал итоговый page/tests и принял их с проверенными fingerprints. Production часть inventory/census, external consumers, observation/removal approval и live rollout остаются открытыми там, где нет фактических данных.

## Publication

Parent создал отдельные verified code commits: census `93f5c84`, backend/contracts `361688b`, frontend `a465a23`. После commits повторно проверены все **30** code files: 18-file backend manifest совпал с CODE review, 12-file census/frontend manifest `eef47b9b84088a8bffe96e795399c2aaa83a19a7de85defd7a0914cdebdb0fe0` совпал с S01/S05 approval. Publication/CI ещё ожидаются; deployment не выполнялся. В workflow rollout допускается только через `workflow_dispatch`, не code push.
