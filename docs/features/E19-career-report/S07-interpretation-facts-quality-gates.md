# S07: Interpretation Facts и quality gates

## Статус

🟡 Частично — curated boundary работает; provenance и semantic quality gates требуют усиления

## Контекст

Перед LLM нужен один ограниченный объект, который соединяет dimensions, archetypes, environment, contradictions, role matches и paths. Без него модель начнёт повторно интерпретировать карту и придумывать причинность.

## Что сделать

1. Определить schema `CareerInterpretationFacts`.
2. Включить top/low dimensions, confidence/evidence refs, Top-3 archetypes, environment/anti-environment, user preferences, contradictions, role matches и paths.
3. Для каждого будущего report section назначить owned/reference/forbidden facts.
4. Добавить deterministic validators:
   - evidence exists and belongs to chart/profile;
   - no direct planet-to-profession claim;
   - no unsupported role/path;
   - contradictions retained;
   - low confidence marked for conditional language;
   - no diagnostic/income/employment guarantees;
   - no raw chart/raw answers in LLM input.
5. Версионировать schema и curation rules.

## Минимальный contract

```json
{
  "contract_version": "career_interpretation_facts_v1",
  "profile_id": "uuid",
  "chart_id": "uuid",
  "scoring_version": "career-mvp-1",
  "top_dimensions": [],
  "low_dimensions": [],
  "career_archetypes": [],
  "preferred_environment": [],
  "risk_environment": [],
  "confirmed_traits": [],
  "contradictions": [],
  "user_preferences": {},
  "role_matches": [],
  "career_paths": []
}
```

## Критерии приёмки

- [x] Schema валидируется до любого LLM вызова.
- [ ] Все выводы имеют реальные source IDs/version lineage без fallback-ссылок на общий chart.
- [x] Section ownership предотвращает повтор и смешение тем.
- [ ] Low confidence принудительно снижает категоричность итоговой прозы и проверяется output validator-ом.
- [x] Unsupported profession/path блокируется до LLM.
- [ ] Contradictions сохраняются в итоговой прозе семантически, а не только формальной citation-ссылкой.
- [x] Snapshot tests доказывают отсутствие raw chart и unrestricted free text.
- [x] Validation failure не запускает платный provider call.

## Реализация и evidence

- `backend/app/modules/career/interpretation_facts.py` — strict curated schema, source/version lineage, section owned/reference/forbidden contracts и pre-provider validation.
- Валидаторы блокируют missing evidence, потерю contradictions, неподдержанные роли/profession examples/paths, raw chart/answers/free text и low-confidence facts без conditional-language marker.
- `backend/tests/unit/test_career/test_interpretation_facts.py` — curated payload, section ownership, provider short-circuit, lineage/contradiction и persistence contracts.
- `uv run pytest tests/unit/test_career/test_interpretation_facts.py -q` → `4 passed`.

## Аудит 2026-09-26

Roles, paths и contradictions не всегда несут конкретные evidence source IDs; часть facts использует fallback `chart:{id}`. Prompt contract содержит conditional-language marker, но output validator не доказывает условную формулировку результата. Citation contradiction key также не доказывает сохранение смысла contradiction в body.
