# S09: Guidance Facts и child-safety gates

## Статус

🟡 Переоткрыто для [BUG-50](../../reviews/2026-10-28/BUG-50-child-content-quality.md): технические safety-гарантии исходного slice проверены, но теряется содержательный контекст средних оценок и тем. Исправление не должно ослаблять эти гарантии.

Дополнительные критерии BUG-50:

- [x] Сохранены поддержанные источниками различия parent/child/interaction и тем наблюдений, включая среднюю зону.
- [x] Ownership не теряет имеющееся тематическое действие и не дублирует несвязанные разделы.
- [x] Новые семантики версионированы; старые immutable facts/hash/read/replay совместимы.
- [x] Семантический quality verdict отделён от технической готовности и подтверждён регрессией реального класса дефекта.

## Контекст

Перед LLM нужен ограниченный детерминированный объект рекомендаций и исполняемые guardrails, иначе модель сможет создавать labels, диагнозы и неподтверждённые советы.

## Что сделать

1. Собрать versioned `ChildGuidanceFacts` из resolver/interaction/age artifacts.
2. Определить section ownership и evidence registry.
3. Реализовать pre-LLM completeness/contradiction/confidence gates.
4. Реализовать post-LLM diagnosis/label/fatalism/blame/unsafe-discipline/age checks.
5. Создать negative corpus на запрещённые формулировки.

## Затрагиваемые файлы

| Область                                                    | Действие          |
| ---------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/guidance_facts.py`              | Изменить/добавить |
| `backend/app/modules/child/quality.py`                     | Изменить/добавить |
| `backend/app/modules/child/safety.py`                      | Изменить/добавить |
| `backend/tests/unit/test_child/test_child_safety_gates.py` | Изменить/добавить |

## Критерии приёмки

- [x] Guidance Facts не содержат raw chart/unrestricted answers.
- [x] Каждое действие поддержано evidence/context rule.
- [x] Low confidence требует условной формулировки.
- [x] Adult-action framing проверяется машинно.
- [x] Negative corpus блокируется до публикации.
- [x] Safety failure не уничтожает deterministic artifact.

## Реализация

- `child-guidance-facts-v1` детерминированно собирается только из validated current Context Resolution, exact eight Interaction rows и pinned Age Snapshot. Payload содержит bounded codes, topic/dimension/applicability ownership, confidence markers и evidence registry без chart payload, answer values, имени, birth data или provider secrets.
- `ChildGuidanceFactsRepository` повторно проходит owner/child/generation route validation через Context Resolution repository, держит source row locks, строит expected artifact заново и fail-closed сравнивает persisted payload/evidence при replay. Concurrent create сериализуется advisory lock и возвращает одну immutable row.
- Для всех 15 report sections определены owned/reference/forbidden fact families, minimum evidence, low-confidence behavior и обязательные safety markers; action-oriented sections дополнительно проверяют owned topic/dimension.
- `guidance_prompt_content()` возвращает exact FR-E22.8 content schema и не включает internal `generation_id`, age metadata или input hash; вложенные domain facts deep-frozen, а prompt/persistence получают независимые JSON-копии.
- Pre-LLM quality gate проверяет exact allowlisted payload, все fact families, schema и membership evidence registry, caregiver-target и allowlisted resolver actions/reasons, confidence markers и executable section ownership.
- Post-LLM gate получает только fact refs и authoritative `ChildGuidanceFacts`: confidence/evidence нельзя подменить caller-ом. Gate блокирует diagnosis/attachment labels, fatal/adult-outcome predictions, ability ranking, fixed labels, blame, medical/legal advice, unsafe discipline, age-inappropriate advice, unsupported/cross-section facts и direct planet-to-child-trait claims. Negative corpus покрывает русские и английские нормативные формулировки.
- Safety rejection не мутирует и не удаляет persisted deterministic `ChildGuidanceFacts`; unsafe section не проходит publication gate.

## Verification

- `uv run pytest tests/unit/test_child/test_child_safety_gates.py -q` — 97 passed;
- `uv run pytest tests/integration/test_child_questionnaire_context.py -q` — 10 passed;
- `uv run pytest tests/unit/test_child -q` — 269 passed;
- все восемь child integration files — 32 passed;
- repo-wide Ruff check и scoped format — PASS;
- strict mypy `app` — PASS (244 source files).

Независимые specification-compliance и code-quality/security review завершены с вердиктами PASS/APPROVED.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
