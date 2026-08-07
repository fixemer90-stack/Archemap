# V2-E1 S03: Define section taxonomy and ownership rules

## Status

✅ Contract docs aligned

## Context

This story belongs to `V2-E1 — Architecture & contracts`.

The upper report is a narrative personality report assembled from bounded LLM-generated sections. Each section receives a builder-created JSON input, not the full unrestricted chart. The section taxonomy and ownership rules prevent duplicated generic horoscope prose.

## Current upper report taxonomy

The canonical sample uses these upper sections:

| Section id | User-facing title | Purpose |
|---|---|---|
| `hero` | Натальный портрет личности | Main portrait / report entrance. |
| `core_pattern` | Ядро личности | Main personality formula and central tension. |
| `perception_and_mind` | Мышление и восприятие | How the person perceives, thinks, explains and checks reality. |
| `emotional_regulation` | Эмоциональная регуляция | Feelings, protection, restoration, emotional timing. |
| `agency_and_desire` | Воля и действие | Drive, action rhythm, resistance, boundaries and effort. |
| `relationships_and_intimacy` | Близость и отношения | Trust, closeness, choice, relational patterns. |
| `growth_vector` | Вектор роста | Mature expression and development direction. |

`technical_basis` is not an upper personality section. In the current sample it is represented by the lower deterministic calculation layer.

## Ownership rules

Each synthesized theme must have:

```text
primary_section: exactly one owner
secondary_sections: optional short references only
forbidden_theme_ids: sections where this theme must not be expanded
```

Renderer rules:

- owned themes: explain fully;
- reference themes: mention briefly only if needed for continuity;
- forbidden themes: do not explain or paraphrase;
- no global `strengths` / `vulnerabilities` buckets in phase 1;
- no separate `sexuality` section in phase 1;
- no archetype or typology summary blocks.

## LLM section behavior

Each LLM request answers one personality question:

```text
core_pattern              → What is the main personality formula?
perception_and_mind       → How does the person process and explain reality?
emotional_regulation      → How does the person feel, defend and recover?
agency_and_desire         → How does the person act, want and resist?
relationships_and_intimacy→ How does the person build trust and closeness?
growth_vector             → What is the mature direction of the chart?
```

The LLM must not decide that a lower calculation card should appear, disappear or move. That belongs to deterministic builders and UI layout.

## Files affected

| Path | Action |
|---|---|
| `docs/architecture/astrotype-v2-natal-report-architecture.md` | Section taxonomy and ownership model. |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md` | Functional requirement for section generation and assembly. |
| `docs/design/astrotype-v2-infographic-db-report-sample.html` | Canonical visual reference, not implementation target for this story. |
| `docs/design/astrotype-v2-infographic-db-report-data.json` | Canonical sample data shape for the visual reference. |

## Acceptance criteria

- [x] Upper section taxonomy matches the canonical sample.
- [x] `technical_basis` is documented as lower deterministic layer, not a prose section/dashboard.
- [x] Ownership rules prevent duplicated expansion across sections.
- [x] Each LLM section has a bounded personality question.
- [x] Deferred “calculation-to-section links” / `Thematic indicator bundles` are excluded from current MVP UI.

## Verification evidence

Same docs-only verification as `FEATURE.md`; stale strings around active thematic bundles / calculation-to-section links were searched and not found as active MVP scope.
