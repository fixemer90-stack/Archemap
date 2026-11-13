# BUG-51: тематические объяснения при средних и смешанных сигналах

## Статус

Исправление реализовано и прошло независимое spec/security/code review без блокирующих замечаний. По согласованию с владельцем после утраты сервера закрытие #51 требует публикации и зелёного CI, но не production rollout. Live-проверка перенесена в [чеклист восстановления](../../deployment/child-post-recovery-verification.md); её выполнение не заявляется.

Актуальный DPAPI PAT проверен и действителен. Предыдущий `401` относился к устаревшей Windows `GH_TOKEN`, а не к актуальному credential. Добавление комментария в issue через текущий PAT было отклонено `Resource not accessible by personal access token (addComment)`; это отдельное ограничение issue-write, не блокировка публикации кода. Production и paid budget не изменялись.

Commits опубликованы в `main`: backend/test repair `4ab17df`, reader/browser coverage `a4afba6`, evidence `3cf1660`; отдельная CI prerequisite `92018c4`. Проверенный code revision — `0115de5358e1519d2a0ef6ab9a4f3b8fbacd345b`; CI [43520765226](https://github.com/fixemer90-stack/Archemap/actions/runs/43520765226) — **8/8 jobs success**, включая полный backend unit/integration, frontend browser/build и обе Docker image builds. Последующий closure commit изменяет только документацию и использует `[skip ci]`, чтобы не повторять неизменённый 21-минутный code pipeline; application/workflow sources проверены как равные этому CI revision. Это не отдельный CI PASS для documentation commit.

Это отдельный follow-up после [BUG-50](../2026-10-28/BUG-50-child-content-quality.md), не завершение эксплуатационных S15–S16 и не разрешение новой платной генерации. Исходные персональные данные и идентификаторы пользователей в этот документ не включены.

## Изменение контракта

Новые полные генерации используют `child-guidance-facts-v4` → `child_section_render_input_v5` → `child-section-prompt-v5` → `child_report_narrative_v5`. Пороги выраженной опоры `score >= 65`, напряжения `score <= 35` и достаточности confidence `>= 0.4` не снижены. Вместо использования этих порогов как запрета на тему тематические interaction measures направляются своему разделу.

| Измерение                               | Раздел-владелец      |
| --------------------------------------- | -------------------- |
| emotional_attunement                    | natural_contact      |
| boundary_fit, tempo_fit                 | friction_zones       |
| soothing_compatibility                  | soothing_support     |
| communication_fit, learning_interaction | explanation_learning |
| conflict_pattern                        | conflict_cycle       |
| autonomy_balance                        | not_personal         |

Тематические наблюдения и действия сохраняют отдельное распределение: soothing → soothing_support, boundaries → boundaries_rules, communication → explanation_learning, transitions → conscious_adjustments, autonomy → autonomy. Поддержанные source profiles, actions, avoid patterns и evidence refs проходят canonical ownership/lineage checks; валидная ссылка не разрешает примешать чужую тему.

У interaction facts появился проверяемый `signal_state`: `ambiguous_signals`, `no_pronounced_skew`, `pronounced_signal`. Отсутствие выбранного наблюдения остаётся отдельным resolver-фактом; оно не стирает имеющийся средний расчётный показатель. Presentation дополнительно возвращает `evidence_state`/`evidence_note`; PDF показывает сохранённое пояснение неопределённости. Reader использует индивидуальную причину для `not_applicable`, но не выдаёт её за объяснение технически упавшего narrative.

Тексты ограничивают вывод: расчёт не восстанавливает последовательность конфликта и не устанавливает намерения ребёнка. Нет новых word/sentence/token quotas или требования заполнить каждый раздел. Старые Guidance Facts V1–V3 и narrative V1–V4 сохраняют свои payload/input/prompt/assembly hashes; resumed V3 full generation остаётся на V4 prompt. Narrative retry сохраняет исходный V4/V5 prompt pin.

## Проверки, повторённые родительским агентом

- При возобновлении незавершённого кандидата `test_thematic_signals_v5.py`: **7 failed, 1 passed**, причиной был отсутствующий `signal_state`, а не недоступность внешнего provider.
- После backend-исправления весь `pytest tests/unit/test_child -q`: **658 passed**, одно предупреждение WeasyPrint о будущей зависимости HarfBuzz-Subset.
- Полный backend `ruff check .` и `ruff format --check .`: PASS, **510 files**. Первый полный `mypy .` нашёл две ошибки optional content в новом тесте; после явной проверки `is not None` повторный полный `mypy .`: **509 source files clean**; targeted thematic suite: **23 passed**.
- Реальный disposable PostgreSQL, mock-only: `pytest tests/integration/test_child_questionnaire_context.py tests/integration/test_child_presentation_pdf.py tests/integration/test_child_content_versions.py tests/integration/test_child_citation_contract_v4.py -q`: **19 passed**, одно предупреждение WeasyPrint. Включены реальное deterministic scoring, commit → fresh-session read, API, rendered PDF extraction, legacy V1–V4 read/retry и сохранность hashes.
- Disposable PostgreSQL родительского прогона `archemap-bug51-parent-test` удалён; отсутствие прочитано через `docker ps -a --filter name=archemap-bug51-parent-test`.
- Playwright `playwright.child.config.ts`, thematic-evidence + quality: **18 passed** на desktop/tablet/mobile. Проверены точные synthetic bodies, причина действительно отсутствующего материала, отказ выдавать evidence note за техническую ошибку, legacy reader, PDF href, отсутствие create/retry и horizontal overflow. Это synthetic API fixtures с реальными компонентами, не native production readback. Mobile screenshot осмотрен.
- Frontend repo-wide ESLint, Prettier, TypeScript: PASS. ESLint оставляет два существующих warning в login/register, без ошибок. `npm test`: все объявленные UX/contract scripts PASS. `npm run build`: PASS.
- Full unit collection: **1437 collected**, без import-file mismatch. Это collection, не утверждение об исполнении полного backend unit suite.
- `git diff --check`: PASS.

## Независимое review и окончательный test-only delta

Read-only reviewer `deleg_3039002c` вернул **APPROVED**, без security concerns и logic errors. Проверенный base HEAD: `92018c4ca7038656be76fe145e7d8320f84c6d94`; SHA256 tracked diff только `backend`/`frontend`: `b3cca8170eece5a1dab03e81f3ff06ee371a1be9e2fd90c17730a66d0cc62b49`. Родительский агент сравнил все перечисленные reviewer file fingerprints с рабочим деревом — совпали. Общий diff также включает отдельные документационные изменения, поэтому его hash отличается.

Reviewer независимо исполнил **241 passed, 1 deselected**, отдельно **23 thematic tests**, frozen compatibility assertions и пять adversarial V5 probes (citation laundering, придуманный конфликт/намерение, отсутствие claims, подмена conditional). Все probes отклонены без сохранения narrative content/output. Его полный 658-test прогон прервался по timeout; это не отдельный full-suite PASS. PostgreSQL и браузерный runtime reviewer не запускал: эти результаты выше получены родительским агентом, а не независимым исполнением.

Неблокирующая рекомендация закреплена в коде: существующая adversarial-output matrix параметризована для V4 и V5, **15 дополнительных V5 cases**. После review изменился только этот тест и документация, production code не менялся. Родительский агент повторил whole-backend Ruff/format/mypy — PASS; весь `pytest tests/unit/test_child -q` после последнего test-only изменения — **673 passed**, одно прежнее предупреждение WeasyPrint.

## Публикация и CI-ремонты

- `6c29cad` опубликован, но run `43515501570` остановлен до создания jobs: GitHub не допускает `runner.temp` в job-level `env`. Это ошибка workflow, не narrative generation.
- `c1b24f9` экспортирует `TMPDIR` из runtime step через `RUNNER_TEMP`/`GITHUB_ENV`. Отдельные RED→GREEN contract tests и Actionlint всех трёх workflows пройдены. Run `43516542772` выявил SIM102 в прежнем Self assembler, который не диагностировал локальный Ruff 0.15.20; на CI установлен Ruff 0.17.5.
- `dc484d9` эквивалентно объединил вложенное условие; соответствующие 14 narrative assembly regressions пройдены. Затем CI выявил два obsolete `no-untyped-call` ignores после типизации Redis factory в Redis 8.1.0.
- `0115de5` удаляет только эти два ignore comments, без изменения Redis runtime logic. Ошибка воспроизведена локально с CI-версиями Redis/Ruff/mypy. Свежие full Ruff/format/mypy и 12 rate-limit/workflow regressions — PASS. Итоговый CI проверяется отдельно, локальный PASS его не заменяет.
- В CI `43520765226` на `0115de5` backend действительно исполнил **1453 unit tests** и **186 integration tests** — оба этапа PASS; это отдельное подтверждение сверх локального Child slice. Полный verdict workflow учитывает также downstream Docker build.
- Push не выполняет rollout: deploy jobs требуют `workflow_dispatch`. В build/push run `43516542839` staging/production deploy jobs подтверждены как skipped; manual dispatch не выполнялся.

## Критерии и оставшаяся приёмка

- [x] Средние показатели доходят до тематических разделов без превращения в strong_matches/friction_points.
- [x] Состояния отсутствующих входов, неоднозначности и отсутствия перекоса различаются в данных и approved text.
- [x] Проверены boundary scores/confidence, missing observations, противоположные сигналы и запрещённые чужие citations.
- [x] Версионирование и frozen historical read/retry/PDF подтверждены тестами.
- [x] Mock-only persistence → fresh session → API → PDF и отдельные desktop/tablet/mobile fixtures проверены.
- [x] Независимое spec/security/code review завершено без блокирующих замечаний; test-only рекомендация реализована и перепроверена.
- [x] Изменения опубликованы; code CI `43520765226` на точном `0115de5358e1519d2a0ef6ab9a4f3b8fbacd345b` — 8/8 success. Последующие documentation-only изменения проверены отдельно.
- [ ] После восстановления инфраструктуры согласована и выполнена live-проверка по отдельному [чеклисту](../../deployment/child-post-recovery-verification.md). **Не блокирует закрытие #51 по согласованию с владельцем**; не считается пройденной проверкой. Новые paid calls требуют отдельного разрешения.

Локальная проверка кода не является production repair. Исторический production V4 report не перезаписывается и не переинтерпретируется; для проверки нового результата требуется явный согласованный rollout/generation scope.
