# V2-E7 S03: Implement segment runner

## Status

✅ Завершено

## Context

This story belongs to `V2-E7 — Modular LLM generation`.

Call the LLM provider per segment, persist request/response/hash/status and support retry. The runner must be designed for large sections: provider token limits are handled through continuation/chunking, not by forcing short report sections.

## Segment lifecycle

```text
SectionRenderInputV2 JSON
→ provider request
→ raw response
→ parse
→ validate
→ persist ReportSegmentGeneration
→ ready / retry / continuation_required / failed
```

## Continuation / chunking policy

If a provider stops because of output/token limit:

1. Persist the partial raw response.
2. Parse and validate the completed part if possible.
3. Send a continuation request for the same `section_id` with:
   - same allowed evidence/theme ids;
   - summary/hash of already accepted text;
   - instruction to continue, not restart;
   - no new facts.
4. Assemble validated parts into one `ReportSegmentV2`.
5. Store part count and continuation lineage.

The runner must not silently truncate long output. No artificial caps may be used to force a valid long section into a short product shape.

## Files likely affected

| Path                                               | Action                                           |
| -------------------------------------------------- | ------------------------------------------------ |
| `backend/app/modules/astrotype_v2/llm_segments.py` | Provider call, continuation and retry lifecycle. |
| `backend/app/modules/astrotype_v2/repositories.py` | Persist segment generation artifacts.            |
| `backend/app/modules/astrotype_v2/schemas.py`      | Segment status/continuation schemas.             |
| `backend/tests/unit/test_astrotype_v2/`            | Runner tests when implementation starts.         |

## Acceptance criteria

- [x] Each segment request/response is persisted.
- [x] Provider failures retry at segment level.
- [x] Output-limit stops trigger continuation instead of final truncation.
- [x] Long valid sections are preserved, not capped.
- [x] Runner records prompt/input/model/provider/version/hash metadata.
- [x] Runner never reruns the full report just because one segment failed.

## Verification commands

Fill with targeted runner tests when implementation starts.
