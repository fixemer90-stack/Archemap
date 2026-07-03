# ruff: noqa: RUF001
"""RED tests for E14 S05 staged orchestration, cache, retry, and statuses."""

from __future__ import annotations

from app.modules.report_narratives.schemas import AssemblyCheck, DeepNatalSynthesis, NarrativePlan
from app.modules.report_narratives.service import (
    build_stage_progress_snapshot,
    compute_stage_input_hashes,
    get_runnable_stages,
    plan_stage_resume,
    reuse_cached_stage_artifacts,
)


def _fake_synthesis() -> DeepNatalSynthesis:
    return DeepNatalSynthesis.model_validate(
        {
            "contract_version": "deep_natal_synthesis_v1",
            "source_chart_snapshot_id": "chart:test",
            "evidence_map": {
                "sun_virgo_house_9": {
                    "id": "sun_virgo_house_9",
                    "label": "Солнце в Деве в 9 доме",
                    "kind": "planet_placement",
                    "source": "chart.planets",
                    "meaning": "Идентичность строится через систему смысла.",
                },
                "moon_opposition_saturn": {
                    "id": "moon_opposition_saturn",
                    "label": "Луна оппозиция Сатурн",
                    "aspect_type": "opposition",
                    "source": "chart.aspects",
                    "meaning": "Чувства быстро встречают внутренний контроль.",
                },
            },
            "ranked_aspects": [
                {
                    "id": "moon_opposition_saturn",
                    "label": "Луна оппозиция Сатурн",
                    "weight": 0.92,
                    "evidence_ids": ["moon_opposition_saturn"],
                    "section_targets": ["emotions_and_communication", "development"],
                }
            ],
            "aspect_patterns": [
                {
                    "id": "saturn_boundary_pattern",
                    "title": "Контроль и уязвимость",
                    "aspect_ids": ["moon_opposition_saturn"],
                    "planets": ["Moon", "Saturn"],
                    "pattern_type": "tension",
                    "psychological_mechanism": "Переживание быстро проходит через фильтр внутреннего контроля.",
                    "life_manifestation": "Человек долго держит важное внутри.",
                    "risk": "Сдерживание может выглядеть как холодность.",
                    "mature_expression": "Сначала назвать переживание, потом решать форму выражения.",
                    "section_targets": ["emotions_and_communication", "development"],
                    "evidence_ids": ["moon_opposition_saturn"],
                    "weight": 0.92,
                }
            ],
            "house_axis_patterns": [
                {
                    "id": "house_axis_house_scenario_sun_9",
                    "title": "Смысл как ось идентичности",
                    "axis": "Дом 9",
                    "mechanism": "Нужно собрать из опыта систему смысла.",
                    "manifestation": "Человек ищет позицию, а не просто впечатления.",
                    "evidence_ids": ["sun_virgo_house_9"],
                    "section_targets": ["main_formula", "world_perception"],
                }
            ],
            "planet_roles": [
                {
                    "id": "planet_role_sun_virgo_house_9",
                    "title": "Солнце в Деве в 9 доме",
                    "function": "Собирает идентичность через анализ и систему взглядов.",
                    "influence": "Даёт потребность занимать обоснованную позицию.",
                    "section_targets": ["main_formula"],
                    "evidence_ids": ["sun_virgo_house_9"],
                }
            ],
            "chart_dynamics": [
                {
                    "id": "chart_dynamic_moon_saturn_regulation",
                    "title": "Напряжение между чувственным импульсом и внутренним контролем",
                    "mechanism": "Реакция быстро встречает внутреннюю проверку.",
                    "tension": "Хочется выразиться и одновременно удержать управление.",
                    "compensation": "Сначала назвать переживание, потом выбирать форму.",
                    "section_targets": ["emotions_and_communication", "development"],
                    "evidence_ids": ["moon_opposition_saturn"],
                }
            ],
            "contradictions": [
                {
                    "id": "contradiction_moon_saturn_expression_vs_control",
                    "title": "Выразить чувство или удержать контроль",
                    "tension": "Выражение и контроль сталкиваются одновременно.",
                    "manifestation": "Снаружи это выглядит как сдержанная включённость.",
                    "mature_expression": "Чувство получает форму, а не подавление.",
                    "evidence_ids": ["moon_opposition_saturn"],
                }
            ],
            "maturity_levels": {
                "low": {
                    "title": "Реактивная защита",
                    "body": "Напряжение проживается автоматично и закрывает контакт.",
                    "evidence_ids": ["moon_opposition_saturn"],
                },
                "medium": {
                    "title": "Осознавание без устойчивости",
                    "body": "Человек уже замечает паттерн, но ещё срывается в старую защиту.",
                    "evidence_ids": ["moon_opposition_saturn"],
                },
                "high": {
                    "title": "Управляемая глубина",
                    "body": "Переживание переводится в выбранный ритм и форму контакта.",
                    "evidence_ids": ["moon_opposition_saturn"],
                },
            },
            "calibration_hypotheses": [
                {
                    "id": "calibration_chart_dynamic_moon_saturn_regulation",
                    "hypothesis": "Когда напряжение растёт, замечаете ли вы, что сначала сдерживаете реакцию?",
                    "answer_type": "scale_1_5",
                    "evidence_ids": ["moon_opposition_saturn"],
                }
            ],
        }
    )


def _fake_plan() -> NarrativePlan:
    return NarrativePlan.model_validate(
        {
            "prompt_version": "self_plan_v2",
            "sections": [
                {
                    "section_id": "identity",
                    "title": "Как собирается ваша идентичность",
                    "required_evidence_ids": ["sun_virgo_house_9"],
                    "focus": "Смысл и позиция как ось личности.",
                },
                {
                    "section_id": "emotional",
                    "title": "Как вы переживаете и выражаете напряжение",
                    "required_evidence_ids": ["moon_opposition_saturn"],
                    "focus": "Чувство проходит через внутренний контроль.",
                },
            ],
            "global_guardrails": ["use only provided evidence ids"],
            "assembly_notes": "Собрать единый Self narrative без повторов.",
        }
    )


def test_compute_stage_input_hashes_returns_stable_hashes_for_plan_sections_and_assembly() -> None:
    hashes = compute_stage_input_hashes(_fake_synthesis(), _fake_plan())

    assert set(hashes) == {"plan", "identity", "emotional", "assembly"}
    assert all(len(value) == 64 for value in hashes.values())
    assert hashes["plan"] != hashes["assembly"]
    assert hashes["identity"] != hashes["emotional"]


def test_reuse_cached_stage_artifacts_preserves_ready_stages_and_reopens_only_failed_stage() -> None:
    synthesis = _fake_synthesis()
    plan = _fake_plan()
    hashes = compute_stage_input_hashes(synthesis, plan)

    existing = {
        "plan": {
            "stage_id": "plan",
            "status": "ready",
            "prompt_version": "self_plan_v2",
            "model_name": "gpt-5.4",
            "input_hash": hashes["plan"],
            "attempt_count": 1,
            "error_message": None,
            "artifact": plan.model_dump(mode="json"),
        },
        "identity": {
            "stage_id": "identity",
            "status": "ready",
            "prompt_version": "self_section_identity_v2",
            "model_name": "gpt-5.4",
            "input_hash": hashes["identity"],
            "attempt_count": 1,
            "error_message": None,
            "artifact": {"section_id": "identity"},
        },
        "emotional": {
            "stage_id": "emotional",
            "status": "failed",
            "prompt_version": "self_section_emotional_v2",
            "model_name": "gpt-5.4",
            "input_hash": hashes["emotional"],
            "attempt_count": 2,
            "error_message": "invalid_response",
            "artifact": None,
        },
        "assembly": {
            "stage_id": "assembly",
            "status": "pending",
            "prompt_version": "self_assemble_v2",
            "model_name": "gpt-5.4",
            "input_hash": hashes["assembly"],
            "attempt_count": 0,
            "error_message": None,
            "artifact": None,
        },
    }

    reused = reuse_cached_stage_artifacts(
        existing_artifacts=existing,
        stage_input_hashes=hashes,
        model_name="gpt-5.4",
    )

    assert reused["plan"].status == "ready"
    assert reused["identity"].status == "ready"
    assert reused["emotional"].status == "pending"
    assert reused["emotional"].attempt_count == 2
    assert reused["emotional"].error_message is None
    assert reused["assembly"].status == "pending"


def test_plan_stage_resume_reuses_ready_siblings_and_regenerates_failed_stage_plus_assembly() -> None:
    synthesis = _fake_synthesis()
    plan = _fake_plan()
    hashes = compute_stage_input_hashes(synthesis, plan)
    artifacts = reuse_cached_stage_artifacts(existing_artifacts={}, stage_input_hashes=hashes, model_name="gpt-5.4")
    artifacts["plan"].status = "ready"
    artifacts["identity"].status = "ready"
    artifacts["identity"].artifact = {"section_id": "identity"}
    artifacts["emotional"].status = "failed"
    artifacts["assembly"].status = "ready"
    artifacts["assembly"].artifact = {"needs_retry": False}

    resume_plan = plan_stage_resume(artifacts)

    assert resume_plan.reused_stages == ["plan", "identity"]
    assert resume_plan.regenerated_stages == ["emotional", "assembly"]
    assert resume_plan.resume_mode == "resume"
    assert resume_plan.reason == "failed_stage:emotional"


def test_get_runnable_stages_waits_for_plan_and_then_unlocks_sections_and_assembly() -> None:
    synthesis = _fake_synthesis()
    plan = _fake_plan()
    hashes = compute_stage_input_hashes(synthesis, plan)

    before_plan = reuse_cached_stage_artifacts(existing_artifacts={}, stage_input_hashes=hashes, model_name="gpt-5.4")
    assert get_runnable_stages(before_plan) == ["plan"]

    before_plan["plan"].status = "ready"
    runnable_after_plan = get_runnable_stages(before_plan)
    assert set(runnable_after_plan) == {"identity", "emotional"}

    before_plan["identity"].status = "ready"
    before_plan["emotional"].status = "ready"
    assert get_runnable_stages(before_plan) == ["assembly"]


def test_build_stage_progress_snapshot_exposes_backward_compatible_high_level_progress() -> None:
    synthesis = _fake_synthesis()
    plan = _fake_plan()
    hashes = compute_stage_input_hashes(synthesis, plan)
    artifacts = reuse_cached_stage_artifacts(existing_artifacts={}, stage_input_hashes=hashes, model_name="gpt-5.4")
    artifacts["plan"].status = "ready"
    artifacts["identity"].status = "ready"
    artifacts["emotional"].status = "running"

    progress = build_stage_progress_snapshot(artifacts, final_check=None)
    assert progress.completed_stages == 2
    assert progress.total_stages == 4
    assert progress.ready is False
    assert progress.current_stage == "emotional"

    artifacts["emotional"].status = "ready"
    artifacts["assembly"].status = "ready"
    final_check = AssemblyCheck.model_validate(
        {
            "duplicate_claim_ids": [],
            "missing_required_evidence_ids": [],
            "tone_notes": [],
            "needs_retry": False,
        }
    )
    finished = build_stage_progress_snapshot(artifacts, final_check=final_check)
    assert finished.ready is True
    assert finished.current_stage is None
