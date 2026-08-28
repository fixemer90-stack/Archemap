# ruff: noqa: RUF001, E501
"""Astrotype v2 report generation background tasks."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, time
from typing import Any, cast
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.chart_engine.chart import build_chart
from app.config import settings
from app.infrastructure.celery_async import run_async_in_worker
from app.infrastructure.database import async_session_factory
from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.chart_adapter import build_natal_chart_rows
from app.modules.astrotype_v2.chart_persistence import persist_natal_chart_rows
from app.modules.astrotype_v2.fact_extractor import (
    build_aspect_fact_rows,
    build_balance_pattern_fact_rows,
    build_placement_fact_rows,
)
from app.modules.astrotype_v2.infographic_data import build_natal_infographic_data_row
from app.modules.astrotype_v2.llm_segments import StructuredSegmentProviderAdapter, run_segment_generation_v2
from app.modules.astrotype_v2.outline import ReportOutlineV2, build_report_outline_row, build_report_outline_v2
from app.modules.astrotype_v2.report_assembler import build_deterministic_natal_report_row, build_natal_report_row
from app.modules.astrotype_v2.repository import AstrotypeV2Repository
from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2
from app.modules.astrotype_v2.segment_inputs import build_section_render_inputs_v2
from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, build_natal_synthesis_row
from app.modules.llm.provider import get_llm_provider
from app.modules.profiles.models import PersonProfile
from workers.celery_app import app

_SOURCE_VERSION = "v2.0"
_ENGINE_VERSION = "0.1.5"
_DETERMINISTIC_PROMPT_VERSION = "astrotype_v2_deterministic_local_v1"
_DETERMINISTIC_PROVIDER = "deterministic"
_DETERMINISTIC_MODEL = "v2-local-runtime"


@app.task(  # type: ignore[untyped-decorator]
    name="astrotype_v2.generate_natal_report",
    bind=True,
    max_retries=settings.LLM_MAX_RETRIES,
    default_retry_delay=30,
    soft_time_limit=max(settings.LLM_TIMEOUT_SECONDS * 4, 600),
    time_limit=max(settings.LLM_TIMEOUT_SECONDS * 4 + 120, 720),
)
def generate_natal_report_v2(
    self: object,
    *,
    profile_id: str,
    user_id: str,
    generation_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """Run the v2 generation pipeline outside the request lifecycle."""

    return run_async_in_worker(
        _generate_natal_report_v2_async(
            profile_id=profile_id,
            user_id=user_id,
            generation_id=generation_id,
            force=force,
        )
    )


async def _generate_natal_report_v2_async(
    *,
    profile_id: str,
    user_id: str,
    generation_id: str,
    force: bool,
) -> dict[str, Any]:
    """Build and persist a ready natal-only v2 report for one owned profile."""

    profile_uuid = uuid.UUID(profile_id)
    user_uuid = uuid.UUID(user_id)
    async with async_session_factory() as db:
        repository = AstrotypeV2Repository(db)
        try:
            existing_report = await repository.get_latest_report_for_profile(
                profile_id=profile_uuid,
                user_id=user_uuid,
            )
            if existing_report is not None and not force:
                return _task_payload(
                    generation_id=generation_id,
                    profile_id=profile_uuid,
                    report=existing_report,
                    status="already_exists",
                    force=force,
                )
            if not force:
                existing_report = await _wait_for_existing_report(
                    repository=repository,
                    profile_id=profile_uuid,
                    user_id=user_uuid,
                )
                if existing_report is not None:
                    return _task_payload(
                        generation_id=generation_id,
                        profile_id=profile_uuid,
                        report=existing_report,
                        status="already_exists",
                        force=force,
                    )

            profile = await _load_profile(db, profile_id=profile_uuid, user_id=user_uuid)
            chart = await _get_or_create_chart(repository=repository, profile=profile, user_id=user_uuid)
            positions = await repository.list_planet_positions_for_chart(chart.id)
            houses = await repository.list_houses_for_chart(chart.id)
            aspects = await repository.list_aspects_for_chart(chart.id)
            balances = await repository.list_balances_for_chart(chart.id)
            patterns = await repository.list_patterns_for_chart(chart.id)

            facts = await repository.list_facts_for_chart(chart.id)
            if not facts:
                facts, evidence = await _create_fact_rows(
                    repository=repository,
                    chart_id=chart.id,
                    positions=positions,
                    aspects=aspects,
                    balances=balances,
                    patterns=patterns,
                )
            else:
                evidence = [row for fact in facts for row in await repository.list_fact_evidence(fact.id)]

            synthesis = await repository.get_synthesis_for_chart(chart.id)
            if synthesis is None:
                synthesis = build_natal_synthesis_row(
                    chart_id=chart.id,
                    facts=facts,
                    facts_version=f"facts:{_SOURCE_VERSION}",
                    source_version=_SOURCE_VERSION,
                )
                await repository.add(synthesis)
                await repository.flush()

            outline = await repository.get_outline_for_chart(chart.id)
            if outline is None:
                outline = build_report_outline_row(
                    synthesis=_synthesis_contract(chart.id, synthesis),
                    source_version=_SOURCE_VERSION,
                )
                await repository.add(outline)
                await repository.flush()

            infographic = await repository.get_infographic_data_for_chart(chart.id)
            if infographic is None:
                infographic = build_natal_infographic_data_row(
                    chart_id=chart.id,
                    positions=positions,
                    houses=houses,
                    aspects=aspects,
                    balances=balances,
                    facts=facts,
                    evidence=evidence,
                    source_version=_SOURCE_VERSION,
                )
                await repository.add(infographic)
                await repository.flush()

            latest_report = await repository.get_latest_report_for_chart(chart.id)
            report = build_deterministic_natal_report_row(
                chart_id=chart.id,
                synthesis_row=synthesis,
                outline_row=outline,
                infographic_row=infographic,
                previous_version=latest_report.version if latest_report is not None else 0,
            )
            report.generation_id = uuid.UUID(generation_id)
            await repository.add(report)
            await repository.flush()
            await db.commit()

            report.status = "narrative_generating"
            report.assembled_payload = report.assembled_payload | {"status": "narrative_generating"}
            await repository.flush()
            await db.commit()

            try:
                segments = await _ensure_ready_segments(
                    repository=repository,
                    chart_id=chart.id,
                    outline=outline,
                    synthesis=_synthesis_contract(chart.id, synthesis),
                )
                complete_report = build_natal_report_row(
                    chart_id=chart.id,
                    synthesis_row=synthesis,
                    outline_row=outline,
                    infographic_row=infographic,
                    segment_rows=segments,
                    previous_version=report.version - 1,
                )
                report.status = complete_report.status
                report.deterministic_payload = complete_report.deterministic_payload
                report.narrative_payload = complete_report.narrative_payload
                report.assembled_payload = complete_report.assembled_payload
                await repository.flush()
                await db.commit()
                return _task_payload(
                    generation_id=generation_id,
                    profile_id=profile_uuid,
                    report=report,
                    status="ready",
                    force=force,
                )
            except Exception as exc:
                await db.rollback()
                report.status = "narrative_failed"
                report.assembled_payload = report.assembled_payload | {"status": "narrative_failed", "error": str(exc)}
                await repository.flush()
                await db.commit()
                return _task_payload(
                    generation_id=generation_id,
                    profile_id=profile_uuid,
                    report=report,
                    status="narrative_failed",
                    force=force,
                )
        except Exception:
            await db.rollback()
            raise


async def _load_profile(db: Any, *, profile_id: uuid.UUID, user_id: uuid.UUID) -> PersonProfile:
    result = await db.execute(
        select(PersonProfile).where(PersonProfile.id == profile_id, PersonProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile not found")
    return cast(PersonProfile, profile)


async def _wait_for_existing_report(
    *,
    repository: AstrotypeV2Repository,
    profile_id: uuid.UUID,
    user_id: uuid.UUID,
) -> models.NatalReport | None:
    """Give an in-flight force generation a chance to commit before non-force work starts."""

    for _ in range(10):
        await asyncio.sleep(0.25)
        existing_report = await repository.get_latest_report_for_profile(profile_id=profile_id, user_id=user_id)
        if existing_report is not None:
            return existing_report
    return None


async def _get_or_create_chart(
    *,
    repository: AstrotypeV2Repository,
    profile: PersonProfile,
    user_id: uuid.UUID,
) -> models.NatalChart:
    if profile.latitude == 0.0 and profile.longitude == 0.0:
        raise ValueError("Координаты места рождения не определены. Укажите место рождения в профиле.")
    birth_time = profile.birth_time or time(12, 0)
    local_tz = ZoneInfo(profile.timezone)
    birth_dt_local = datetime.combine(profile.birth_date, birth_time).replace(tzinfo=local_tz)
    birth_dt_utc = birth_dt_local.astimezone(UTC)
    input_payload = {
        "profile_id": str(profile.id),
        "birth_date": profile.birth_date.isoformat(),
        "birth_time": birth_time.isoformat(),
        "birth_time_accuracy": profile.birth_time_accuracy,
        "birth_place": profile.birth_place,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "timezone": profile.timezone,
    }
    input_hash = _stable_hash(input_payload)
    existing_chart = await repository.get_chart_by_profile_engine_input(
        profile_id=profile.id,
        engine_version=_ENGINE_VERSION,
        input_hash=input_hash,
    )
    if existing_chart is not None:
        return existing_chart

    chart_data = build_chart(
        birth_datetime=birth_dt_utc,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone_name=profile.timezone,
    )
    rows = build_natal_chart_rows(
        chart_data=chart_data,
        user_id=user_id,
        profile_id=profile.id,
        engine_version=_ENGINE_VERSION,
        input_hash=input_hash,
    )
    await persist_natal_chart_rows(repository, rows)
    return rows.chart


async def _create_fact_rows(
    *,
    repository: AstrotypeV2Repository,
    chart_id: uuid.UUID,
    positions: list[models.NatalPlanetPosition],
    aspects: list[models.NatalAspect],
    balances: list[models.NatalChartBalance],
    patterns: list[models.NatalChartPattern],
) -> tuple[list[models.NatalFact], list[models.NatalFactEvidence]]:
    placement_facts, placement_evidence = build_placement_fact_rows(chart_id=chart_id, positions=positions)
    balance_facts, balance_evidence = build_balance_pattern_fact_rows(
        chart_id=chart_id,
        balances=balances,
        patterns=patterns,
    )
    aspect_facts, aspect_evidence = await build_aspect_fact_rows(
        repository,
        chart_id=chart_id,
        aspects=aspects,
    )
    facts = [*placement_facts, *balance_facts, *aspect_facts]
    evidence = [*placement_evidence, *balance_evidence, *aspect_evidence]
    await repository.add_many(facts)
    await repository.add_many(evidence)
    await repository.flush()
    return facts, evidence


async def _ensure_ready_segments(
    *,
    repository: AstrotypeV2Repository,
    chart_id: uuid.UUID,
    outline: models.ReportOutline,
    synthesis: NatalSynthesisV2,
) -> list[models.ReportSegmentGeneration]:
    existing_segments = await repository.list_segments_for_outline(outline.id)
    if settings.LLM_ENABLED:
        return await _ensure_llm_segments(
            repository=repository,
            outline=outline,
            synthesis=synthesis,
            existing_segments=existing_segments,
        )
    return await _ensure_deterministic_segments(
        repository=repository,
        chart_id=chart_id,
        outline=outline,
        synthesis=synthesis,
        existing_segments=existing_segments,
    )


async def _ensure_llm_segments(
    *,
    repository: AstrotypeV2Repository,
    outline: models.ReportOutline,
    synthesis: NatalSynthesisV2,
    existing_segments: list[models.ReportSegmentGeneration],
) -> list[models.ReportSegmentGeneration]:
    by_key = {segment.section_key: segment for segment in existing_segments}
    llm_provider = get_llm_provider()
    segment_provider = StructuredSegmentProviderAdapter(
        provider=llm_provider,
        provider_name=settings.LLM_PROVIDER,
        model_name=settings.LLM_MODEL,
    )
    section_inputs = build_section_render_inputs_v2(
        outline=_outline_contract_from_row(outline=outline, synthesis=synthesis),
        synthesis=synthesis,
    )
    generation_inputs = [
        section_input
        for section_input in section_inputs
        if not (
            (existing := by_key.get(section_input.section_id)) is not None
            and existing.status == "ready"
            and existing.provider == settings.LLM_PROVIDER
            and existing.model == settings.LLM_MODEL
        )
    ]
    generated_segments = await asyncio.gather(
        *(
            run_segment_generation_v2(
                provider=segment_provider,
                section_input=section_input,
                outline_id=outline.id,
            )
            for section_input in generation_inputs
        )
    )

    new_segments: list[models.ReportSegmentGeneration] = []
    for segment in generated_segments:
        existing = by_key.get(segment.section_key)
        if existing is not None:
            existing.status = segment.status
            existing.provider = segment.provider
            existing.model = segment.model
            existing.prompt_version = segment.prompt_version
            existing.payload = segment.payload
            existing.error = segment.error
            continue
        new_segments.append(segment)
    if new_segments:
        await repository.add_many(new_segments)
        await repository.flush()
        existing_segments = await repository.list_segments_for_outline(outline.id)
    return existing_segments


async def _ensure_deterministic_segments(
    *,
    repository: AstrotypeV2Repository,
    chart_id: uuid.UUID,
    outline: models.ReportOutline,
    synthesis: NatalSynthesisV2,
    existing_segments: list[models.ReportSegmentGeneration],
) -> list[models.ReportSegmentGeneration]:
    by_key = {segment.section_key: segment for segment in existing_segments}
    section_plans = outline.outline.get("sections", []) if isinstance(outline.outline, dict) else []
    new_segments: list[models.ReportSegmentGeneration] = []
    for section in section_plans:
        section_id = str(section.get("id"))
        if section.get("grounding_status") == "skipped":
            continue
        existing = by_key.get(section_id)
        output = _segment_output(section=section, synthesis=synthesis)
        response_payload = output.model_dump(mode="json")
        payload = {
            "request_hash": _stable_hash({"section": section}),
            "response_hash": _stable_hash(response_payload),
            "response": response_payload,
        }
        if existing is not None:
            existing.status = "ready"
            existing.provider = _DETERMINISTIC_PROVIDER
            existing.model = _DETERMINISTIC_MODEL
            existing.prompt_version = _DETERMINISTIC_PROMPT_VERSION
            existing.payload = payload
            existing.error = None
            continue
        new_segments.append(
            models.ReportSegmentGeneration(
                chart_id=chart_id,
                outline_id=outline.id,
                section_key=section_id,
                status="ready",
                provider=_DETERMINISTIC_PROVIDER,
                model=_DETERMINISTIC_MODEL,
                prompt_version=_DETERMINISTIC_PROMPT_VERSION,
                payload=payload,
                error=None,
            )
        )
    if new_segments:
        await repository.add_many(new_segments)
        await repository.flush()
        existing_segments = await repository.list_segments_for_outline(outline.id)
    return existing_segments


def _segment_output(*, section: dict[str, Any], synthesis: NatalSynthesisV2) -> ReportSegmentOutputV2:
    section_id = str(section.get("id"))
    title = str(section.get("title") or section_id.replace("_", " ").title())
    owned_theme_ids = [str(item) for item in section.get("owned_theme_ids", [])]
    if not owned_theme_ids and synthesis.dominant_themes:
        owned_theme_ids = [synthesis.dominant_themes[0].id]
    evidence_ids = [str(item) for item in section.get("evidence_ids", [])]
    theme_by_id = {theme.id: theme for theme in synthesis.dominant_themes}
    if not evidence_ids and owned_theme_ids:
        evidence_ids = list(theme_by_id.get(owned_theme_ids[0], synthesis.dominant_themes[0]).evidence_ids)
    owned_themes = [theme_by_id[theme_id] for theme_id in owned_theme_ids if theme_id in theme_by_id]
    body = _deterministic_section_body(section_id=section_id, themes=owned_themes)
    return ReportSegmentOutputV2(
        section_id=section_id,
        title=title,
        body=body,
        covered_theme_ids=owned_theme_ids,
        evidence_ids=evidence_ids,
        continuation_complete=True,
        notes=["generated by local deterministic v2 worker"],
    )


def _deterministic_section_body(*, section_id: str, themes: list[Any]) -> str:
    placements = _placements_from_themes(themes)
    aspects = _aspects_from_themes(themes)
    balances = _balances_from_themes(themes)
    top_houses = _top_balance_keys(balances, "house", limit=2)
    top_elements = _top_balance_keys(balances, "element", limit=2)
    top_modalities = _top_balance_keys(balances, "modality", limit=1)

    if section_id == "core_pattern":
        asc = _placement_text(placements, "ascendant")
        sun = _placement_text(placements, "sun")
        moon = _placement_text(placements, "moon")
        mercury = _placement_text(placements, "mercury")
        mars = _placement_text(placements, "mars")
        core_points = [item for item in [asc, sun, moon] if item]
        mental_points = [item for item in [mercury, mars] if item]
        aspect_text = _aspect_sentence(aspects)
        element_text = _balance_sentence(top_elements, "стихия")
        modality_text = _balance_sentence(top_modalities, "модальность")
        house_text = _house_sentence(top_houses)
        return "\n\n".join(
            [
                (
                    "Ядро личности в этом отчёте — не отдельный тип и не ярлык. Это главная связка карты: "
                    "как человек входит в контакт, что держит его самоощущение и через какой внутренний ритм он "
                    "собирает решения. В этой карте основу задают "
                    f"{_join_ru(core_points) or 'ключевые личные точки карты'}."
                ),
                (
                    "Первое впечатление и способ действовать не обязаны совпадать с тем, что происходит внутри. "
                    f"{_core_sentence(asc, 'Асцендент показывает первичную реакцию на мир')}; "
                    f"{_core_sentence(sun, 'Солнце описывает устойчивую линию самости')}; "
                    f"{_core_sentence(moon, 'Луна показывает эмоциональную потребность и способ восстановления')}. "
                    "Поэтому ядро лучше читать как живой механизм, а не как набор положений."
                ),
                (
                    f"{element_text} {modality_text} {house_text} "
                    f"{_core_sentence(_join_ru(mental_points), 'Мышление и действие добавляют к этой формуле свой темп')}. "
                    f"{aspect_text} В зрелом проявлении эта карта сильна там, где внутренний импульс получает форму: "
                    "сначала считывается ситуация, затем появляется ясная формулировка, и только после этого энергия "
                    "уходит в выбранное действие."
                ),
            ]
        )

    if section_id == "perception_and_mind":
        mercury = _placement_text(placements, "mercury")
        return "\n\n".join(
            [
                (
                    "Мышление здесь лучше описывать через способ собирать сигналы, а не через сухой список планет. "
                    f"{_sentence_or_default(mercury, 'Меркурий показывает, как человек формулирует, проверяет и удерживает мысль.')}"
                ),
                (
                    "Восприятие работает как фильтр: сначала нужно заметить оттенок ситуации, потом найти точные слова "
                    "и только после этого делать вывод. Из-за этого человек может казаться переменчивым снаружи, но "
                    "внутри он просто перепроверяет смысл, прежде чем закрепить позицию."
                ),
                (
                    "Сильная сторона такого ума — способность связывать детали в понятную картину. Риск появляется, "
                    "когда уточнение превращается в задержку: мысль уже достаточно ясна, но ей всё ещё хочется ещё одного "
                    "подтверждения."
                ),
            ]
        )

    if section_id == "emotional_regulation":
        moon = _placement_text(placements, "moon")
        return "\n\n".join(
            [
                (
                    "Эмоциональная регуляция показывает, как человек восстанавливает внутреннее равновесие после "
                    "напряжения. Это не про то, насколько он эмоционален внешне, а про то, где психика ищет безопасность. "
                    f"{_sentence_or_default(moon, 'Луна задаёт базовую эмоциональную потребность.')}"
                ),
                (
                    "Чувство здесь лучше обрабатывается, когда ему дают форму: назвать, отделить факт от тревоги, "
                    "понять, какая граница была задета. Если этого времени нет, реакция может уйти в защиту, паузу "
                    "или попытку всё рационализировать."
                ),
                (
                    "Зрелая стратегия — не подавлять сигнал, а распознавать его раньше. Тогда эмоциональная глубина "
                    "не превращается в хаос и не требует немедленного контроля над всем происходящим."
                ),
            ]
        )

    if section_id == "agency_and_desire":
        mars = _placement_text(placements, "mars")
        return "\n\n".join(
            [
                (
                    "Воля и действие описывают, как включается энергия выбора. Здесь важен не абстрактный напор, "
                    "а момент, когда человек внутренне признаёт: это моё направление, сюда стоит вкладываться. "
                    f"{_sentence_or_default(mars, 'Марс показывает стиль действия и сопротивления.')}"
                ),
                (
                    "Если цель чужая или задана давлением, энергия может рассыпаться. Если цель понятна и связана с "
                    "личным смыслом, появляется выносливость: можно возвращаться к задаче, поправлять детали и держать курс."
                ),
                (
                    "Зрелое действие здесь начинается с честного внутреннего да или нет. Чем раньше проговорены условия, "
                    "границы и цена решения, тем меньше саботажа и тем больше настоящей силы в движении."
                ),
            ]
        )

    if section_id == "relationships_and_intimacy":
        venus = _placement_text(placements, "venus")
        return "\n\n".join(
            [
                (
                    "Близость строится не только на симпатии, а на ощущении, что контакт выдерживает реальность. "
                    f"{_sentence_or_default(venus, 'Венера показывает язык привязанности, вкуса и выбора в отношениях.')}"
                ),
                (
                    "Человеку важно видеть, как другой обращается с границами, конфликтом и уязвимостью. Если слова "
                    "совпадают с действиями, доверие растёт. Если контакт требует угадывать или постоянно защищаться, "
                    "включается дистанция."
                ),
                (
                    "Зрелая форма отношений для такой карты — ясность без холодности. Договорённости, уважение к личному "
                    "пространству и честный разговор до накопления напряжения дают больше близости, чем драматичная интенсивность."
                ),
            ]
        )

    return "\n\n".join(
        [
            "Вектор роста показывает, во что может собраться карта, когда человек перестаёт жить только привычной защитой.",
            (
                "Главная задача — соединить устойчивость и движение: не ждать идеальной ясности, но и не бросаться "
                "в случайный импульс. Развитие начинается с права на черновик, проверку и постепенное уточнение формы."
            ),
            (
                "Зрелая версия этой карты появляется там, где человек сохраняет чувствительность, но не теряет опору; "
                "строит планы, но не превращает их в клетку; выбирает ответственность, но оставляет место живому смыслу."
            ),
        ]
    )


def _placements_from_themes(themes: list[Any]) -> dict[str, tuple[str, str]]:
    placements: dict[str, tuple[str, str]] = {}
    for theme in themes:
        for fact_key in getattr(theme, "fact_keys", ()):
            parts = str(fact_key).split(":")
            if len(parts) == 4 and parts[0] == "placement":
                placements[parts[1]] = (parts[2], parts[3].replace("house_", ""))
    return placements


def _aspects_from_themes(themes: list[Any]) -> list[tuple[str, str, str]]:
    aspects: list[tuple[str, str, str]] = []
    for theme in themes:
        for fact_key in getattr(theme, "fact_keys", ()):
            parts = str(fact_key).split(":")
            if len(parts) == 4 and parts[0] == "aspect":
                aspects.append((parts[1], parts[2], parts[3]))
    return aspects


def _balances_from_themes(themes: list[Any]) -> list[tuple[str, str, float]]:
    balances: list[tuple[str, str, float]] = []
    for theme in themes:
        for fact_key in getattr(theme, "fact_keys", ()):
            parts = str(fact_key).split(":")
            if len(parts) == 3 and parts[0] == "balance":
                balances.append((parts[1], parts[2], float(getattr(theme, "weight", 0.0))))
    return balances


def _placement_text(placements: dict[str, tuple[str, str]], body: str) -> str | None:
    placement = placements.get(body)
    if placement is None:
        return None
    sign, house = placement
    body_label = _BODY_LABELS.get(body, body)
    sign_label = _SIGN_LABELS.get(sign, sign)
    if body == "ascendant":
        return f"Асцендент в {sign_label} в {house} доме"
    if body == "mc":
        return f"MC в {sign_label} в {house} доме"
    return f"{body_label} в {sign_label} в {house} доме"


def _top_balance_keys(balances: list[tuple[str, str, float]], category: str, *, limit: int) -> list[str]:
    rows = [(key, value) for raw_category, key, value in balances if raw_category == category]
    return [key for key, _ in sorted(rows, key=lambda item: item[1], reverse=True)[:limit]]


def _aspect_sentence(aspects: list[tuple[str, str, str]]) -> str:
    if not aspects:
        return "Аспекты уточняют, где эта формула получает поддержку или напряжение."
    labels = [
        f"{_BODY_LABELS.get(left, left)} {_ASPECT_LABELS.get(aspect, aspect)} {_BODY_LABELS.get(right, right)}"
        for left, right, aspect in aspects[:3]
    ]
    return f"Ключевые связки: {_join_ru(labels)}; они показывают, где личная энергия получает поддержку или напряжение."


def _balance_sentence(keys: list[str], label: str) -> str:
    if not keys:
        return "Баланс карты добавляет к этому собственный темперамент."
    translated = [_BALANCE_LABELS.get(key, key) for key in keys]
    return f"В балансе заметна {label}: {_join_ru(translated)}."


def _house_sentence(houses: list[str]) -> str:
    if not houses:
        return "Акцент домов показывает, где эта энергия чаще всего становится видимой."
    labels = [f"{house} дом" for house in houses]
    return f"Сильнее всего тема проявляется через {_join_ru(labels)}."


def _core_sentence(value: str | None, default: str) -> str:
    return value or default


def _sentence_or_default(value: str | None, default: str) -> str:
    return f"{value}." if value else default


def _join_ru(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} и {items[-1]}"


_BODY_LABELS = {
    "ascendant": "Асцендент",
    "mc": "MC",
    "sun": "Солнце",
    "moon": "Луна",
    "mercury": "Меркурий",
    "venus": "Венера",
    "mars": "Марс",
    "jupiter": "Юпитер",
    "saturn": "Сатурн",
    "uranus": "Уран",
    "neptune": "Нептун",
    "pluto": "Плутон",
    "north_node": "Северный узел",
    "lilith": "Лилит",
}

_SIGN_LABELS = {
    "aries": "Овне",
    "taurus": "Тельце",
    "gemini": "Близнецах",
    "cancer": "Раке",
    "leo": "Льве",
    "virgo": "Деве",
    "libra": "Весах",
    "scorpio": "Скорпионе",
    "sagittarius": "Стрельце",
    "capricorn": "Козероге",
    "aquarius": "Водолее",
    "pisces": "Рыбах",
}

_ASPECT_LABELS = {
    "conjunction": "соединение",
    "opposition": "оппозиция",
    "trine": "трин",
    "square": "квадрат",
    "sextile": "секстиль",
    "quincunx": "квинконс",
}

_BALANCE_LABELS = {
    "fire": "огонь",
    "earth": "земля",
    "air": "воздух",
    "water": "вода",
    "cardinal": "кардинальность",
    "fixed": "фиксированность",
    "mutable": "мутабельность",
}


def _outline_contract_from_row(*, outline: models.ReportOutline, synthesis: NatalSynthesisV2) -> ReportOutlineV2:
    """Rebuild the typed outline contract used by section input builders."""

    return build_report_outline_v2(synthesis=synthesis, source_version=outline.source_version)


def _synthesis_contract(chart_id: uuid.UUID, synthesis_row: models.NatalSynthesis) -> NatalSynthesisV2:
    payload = synthesis_row.payload
    return NatalSynthesisV2(
        chart_id=chart_id,
        source_version=str(payload.get("source_version", _SOURCE_VERSION)),
        dominant_themes=tuple(_theme_from_payload(item) for item in payload.get("dominant_themes", [])),
        tensions=tuple(_theme_from_payload(item) for item in payload.get("tensions", [])),
        resources=tuple(_theme_from_payload(item) for item in payload.get("resources", [])),
        growth_vectors=tuple(_theme_from_payload(item) for item in payload.get("growth_vectors", [])),
        input_fact_keys=list(payload.get("input_fact_keys", [])),
    )


def _theme_from_payload(payload: dict[str, Any]) -> Any:
    from app.modules.astrotype_v2.synthesis import SynthesisThemeV2

    return SynthesisThemeV2(
        id=str(payload["id"]),
        title=str(payload["title"]),
        summary=str(payload["summary"]),
        primary_section=str(payload["primary_section"]),
        fact_keys=tuple(str(item) for item in payload.get("fact_keys", [])),
        evidence_ids=tuple(str(item) for item in payload.get("evidence_ids", [])),
        weight=float(payload.get("weight", 0.0)),
        confidence=float(payload.get("confidence", 0.0)),
        polarity=payload.get("polarity"),
        fact_type=payload.get("fact_type"),
    )


def _task_payload(
    *,
    generation_id: str,
    profile_id: uuid.UUID,
    report: models.NatalReport,
    status: str,
    force: bool,
) -> dict[str, Any]:
    return {
        "contract_version": "astrotype_v2_generation_task_v1",
        "generation_id": generation_id,
        "profile_id": str(profile_id),
        "report_id": str(report.id),
        "status": status,
        "report_status": report.status,
        "force": force,
    }


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
