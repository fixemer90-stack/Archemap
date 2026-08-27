# Astrotype v2 section evidence grounding remediation

## Purpose

This document defines how Astrotype v2 must fix the production failure where natal report generation can fail because upper report sections do not receive enough section-specific facts/evidence.

Production incident observed on 2026-08-27:

- requested identifier: `2faa0ed3-a4a6-400a-85f3-97a6a1c295ba`;
- no row existed in `astrotype_v2_natal_reports` for that id;
- worker logs showed repeated `astrotype_v2.generate_natal_report` failures;
- primary exception: `SegmentValidationError("missing evidence ids")`;
- one related provider-shape failure also occurred: `LLMInvalidResponseError("LLM provider returned non-JSON content ...")`.

The immediate failure happened in segment validation, but the root cause was earlier: deterministic fact synthesis did not produce enough section-owned evidence for every report section that the LLM runtime attempted to generate.

## Current root cause

The current pipeline creates many technical chart facts, but it classifies them by source type rather than by product section role.

Current extraction hints:

```python
section_hint="placements"
section_hint="balances"
section_hint="patterns"
section_hint="aspects"
```

Current synthesis mapping:

```python
_SECTION_BY_HINT = {
    "placements": "core_pattern",
    "balances": "core_pattern",
    "aspects": "core_pattern",
    "patterns": "growth_vector",
}
```

As a result, production charts may contain about 50-60 facts, but their section coverage is effectively:

| Report section | Typical fact coverage |
|---|---:|
| `core_pattern` | 45-60 facts |
| `perception_and_mind` | 0 facts |
| `emotional_regulation` | 0 facts |
| `agency_and_desire` | 0 facts |
| `relationships_and_intimacy` | 0 facts |
| `growth_vector` | 1-2 facts |

The outline still creates all six sections:

```python
SECTION_ORDER = [
    "core_pattern",
    "perception_and_mind",
    "emotional_regulation",
    "agency_and_desire",
    "relationships_and_intimacy",
    "growth_vector",
]
```

For empty sections, `SectionRenderInputV2.evidence_ids` may be empty. DeepSeek then has no valid evidence ids to return. The validator correctly rejects empty output evidence:

```python
if not output_evidence_ids:
    raise SegmentValidationError("missing evidence ids")
```

The validation error is therefore a symptom. The architectural bug is insufficient semantic distribution of facts across report sections.

## Target behavior

Astrotype v2 must guarantee that every generated narrative section is grounded before it reaches the LLM.

A section is generatable only when it has enough factual basis from one or more of:

1. owned section facts;
2. allowed reference facts from adjacent sections;
3. explicit bridging facts derived for the section from reusable technical facts.

If this invariant is not satisfied, the system must not send an impossible prompt to the LLM.

## Section grounding invariant

Before LLM generation, every section in the generation plan must satisfy:

```text
len(section.evidence_ids) >= MIN_SECTION_EVIDENCE_IDS
and len(section.owned_theme_ids) >= MIN_SECTION_OWNED_THEMES
```

Recommended MVP thresholds:

| Section | Min owned themes | Min evidence ids | Notes |
|---|---:|---:|---|
| `core_pattern` | 3 | 5 | central synthesis can use the strongest cross-chart facts |
| `perception_and_mind` | 2 | 3 | Mercury, air signs, 3/6/9 houses, Mercury aspects |
| `emotional_regulation` | 2 | 3 | Moon, water signs, 4/8/12 houses, Moon aspects |
| `agency_and_desire` | 2 | 3 | Mars, Sun, fire signs, 1/5/10 houses, Mars/Sun aspects |
| `relationships_and_intimacy` | 2 | 3 | Venus, Moon, 7/8 houses, Venus/Moon relational aspects |
| `growth_vector` | 2 | 3 | Saturn, Jupiter, nodes when available, 9/10/12 houses, strong patterns |

The exact thresholds may be tuned, but zero-evidence generated sections are forbidden.

## Thematic assignment model

Fact extraction must keep technical evidence stable, while synthesis must create section-specific usages.

Do not replace source facts. Add a semantic layer that says: this technical fact can support these report sections with these weights.

Recommended internal contract:

```python
@dataclass(frozen=True)
class SectionFactUsageV2:
    fact_key: str
    evidence_id: str
    section_id: str
    role: str
    weight: float
    reason: str
```

A single technical fact may produce multiple section usages. Example: Moon-Mercury aspect can support both `emotional_regulation` and `perception_and_mind`.

## Assignment rules

### Planet/body placements

| Signal | Primary section candidates |
|---|---|
| Sun, Ascendant, strongest angular planets | `core_pattern`, `agency_and_desire` |
| Moon | `emotional_regulation`, `relationships_and_intimacy` |
| Mercury | `perception_and_mind` |
| Venus | `relationships_and_intimacy`, `agency_and_desire` |
| Mars | `agency_and_desire` |
| Jupiter | `growth_vector`, `core_pattern` |
| Saturn | `growth_vector`, `emotional_regulation` when constraint/protection is prominent |
| Uranus/Neptune/Pluto | `growth_vector`, plus section indicated by aspect partner/house |
| Ascendant | `core_pattern`, `agency_and_desire` |
| MC | `growth_vector`, `agency_and_desire` |

### House placements

| House | Primary section candidates |
|---|---|
| 1 | `core_pattern`, `agency_and_desire` |
| 2 | `agency_and_desire`, `relationships_and_intimacy` |
| 3 | `perception_and_mind` |
| 4 | `emotional_regulation` |
| 5 | `agency_and_desire`, `relationships_and_intimacy` |
| 6 | `perception_and_mind`, `growth_vector` |
| 7 | `relationships_and_intimacy` |
| 8 | `relationships_and_intimacy`, `emotional_regulation` |
| 9 | `growth_vector`, `perception_and_mind` |
| 10 | `growth_vector`, `agency_and_desire` |
| 11 | `relationships_and_intimacy`, `growth_vector` |
| 12 | `emotional_regulation`, `growth_vector` |

### Signs/elements/modalities

| Signal | Primary section candidates |
|---|---|
| Air emphasis, Gemini, Virgo | `perception_and_mind` |
| Water emphasis, Cancer, Scorpio, Pisces | `emotional_regulation`, `relationships_and_intimacy` |
| Fire emphasis, Aries, Leo, Sagittarius | `agency_and_desire` |
| Earth emphasis, Taurus, Virgo, Capricorn | `core_pattern`, `growth_vector` |
| Cardinal emphasis | `agency_and_desire` |
| Fixed emphasis | `core_pattern`, `emotional_regulation` |
| Mutable emphasis | `perception_and_mind`, `growth_vector` |

### Aspects

Aspect facts should be assigned using both aspect participants and aspect type.

Examples:

| Aspect signal | Section candidates |
|---|---|
| Mercury involved | `perception_and_mind` |
| Moon involved | `emotional_regulation` |
| Venus involved | `relationships_and_intimacy` |
| Mars involved | `agency_and_desire` |
| Saturn/Jupiter involved | `growth_vector` |
| Sun/Ascendant involved | `core_pattern` |
| tension aspects to Moon/Venus | `emotional_regulation`, `relationships_and_intimacy` |
| tension aspects to Mars/Sun | `agency_and_desire` |
| harmonious aspects to Mercury | `perception_and_mind` |

### Balance and pattern facts

Balance/pattern facts must not be dumped into `core_pattern` by default. They should create usages according to the dimension they describe:

- element balance -> section candidates from element table;
- modality balance -> action/regulation/perception candidates from modality table;
- house emphasis -> section candidates from house table;
- pattern emphasis -> section candidates from the emphasized balance category.

## Outline requirements

`ReportOutlineV2` must be built from section fact usages, not only from fact source hints.

Each `SectionPlanV2` must expose:

- `owned_theme_ids`: themes primarily assigned to this section;
- `reference_theme_ids`: themes from adjacent sections allowed for continuity;
- `evidence_ids`: the exact evidence ids the LLM is allowed and expected to cite;
- `grounding_status`: `ready`, `bridged`, `skipped`, or `blocked`;
- `grounding_reason`: short diagnostic string for logs/API/debug view.

Recommended statuses:

| Status | Meaning | Runtime behavior |
|---|---|---|
| `ready` | section has enough owned evidence | generate normally |
| `bridged` | section lacks owned evidence but has approved reference/bridge evidence | generate with explicit bridging prompt |
| `skipped` | section is intentionally omitted for this chart/profile because it has no grounding | do not call LLM; omit or show deterministic placeholder depending UX contract |
| `blocked` | invariant violation or unexpected empty evidence | fail fast before LLM with actionable diagnostic |

MVP should prefer `bridged` for core product sections and `blocked` for unexpected internal inconsistencies. It must never silently call the LLM with `evidence_ids=[]`.

## Runtime failure handling

A single bad section must not roll back all deterministic work.

Hard deterministic-first delivery invariant:

```text
No LLM provider call before deterministic report commit.
```

See `docs/architecture/astrotype-v2-deterministic-first-delivery.md` for the full transaction/API/frontend contract. This grounding remediation depends on that boundary: section evidence failures are narrative-layer failures and must not prevent the deterministic report shell from being visible.

Required behavior:

1. Persist chart, facts, synthesis, outline and infographic before LLM segment generation.
2. Generate each segment independently.
3. Persist per-segment status:
   - `ready`
   - `running`
   - `failed_validation`
   - `failed_provider`
   - `skipped_ungrounded`
4. Assemble report as:
   - `complete` when all required sections are ready;
   - `partial` when deterministic foundation and at least one narrative section are ready;
   - `failed` only when no user-visible report can be assembled.
5. Keep `generation_id` traceable from API response to Celery task and persisted status rows.

## API/observability requirements

The generation status endpoint must stop returning only synthetic `queued_or_running`.

It must expose at least:

```json
{
  "generation_id": "...",
  "status": "queued|running|partial|complete|failed",
  "report_id": "...",
  "sections": [
    {
      "section_id": "perception_and_mind",
      "grounding_status": "ready|bridged|skipped|blocked",
      "owned_evidence_count": 3,
      "reference_evidence_count": 2,
      "segment_status": "ready|running|failed_validation|failed_provider|skipped_ungrounded",
      "error": null
    }
  ]
}
```

Worker logs must include:

- `generation_id`;
- Celery task id;
- profile id;
- report id when available;
- section id;
- grounding status;
- owned/reference/total evidence counts;
- provider/model;
- validation/provider error class.

## Rollout plan

1. Add tests that reproduce the current failure using a synthesis where only `core_pattern` has owned evidence.
2. Add section fact usage assignment and coverage diagnostics.
3. Update outline builder to use section usages and mark grounding statuses.
4. Block or bridge ungrounded sections before LLM calls.
5. Persist generation/job/section statuses so production incidents are traceable by generation id.
6. Change worker orchestration so one segment failure does not roll back deterministic artifacts.
7. Run production smoke with real provider enabled and verify that every generated section has non-empty evidence ids.

## Acceptance checks

Implementation is not complete until all checks pass:

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_fact_section_assignment.py -v --tb=short
uv run pytest tests/unit/test_astrotype_v2/test_outline.py tests/unit/test_astrotype_v2/test_segment_inputs.py -v --tb=short
uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py -v --tb=short
uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```

Production smoke must prove:

- a new report reaches `complete` or `partial` without rollback;
- status endpoint can be queried by `generation_id`;
- every generated section has `evidence_ids.length > 0`;
- worker logs contain the section-level grounding ledger.
