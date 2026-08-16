#!/usr/bin/env node

import assert from "node:assert/strict";

const { buildV2ReportReaderViewModel } =
  await import("../src/lib/astrotype-v2/report-view-model.ts");

const samplePayload = {
  contract_version: "astrotype_v2_report_api_v1",
  report: {
    id: "report-1",
    chart_id: "chart-1",
    status: "ready",
    version: 1,
    deterministic_payload: {},
    narrative_payload: {
      section_order: [
        "core_pattern",
        "perception_and_mind",
        "emotional_regulation",
        "agency_and_desire",
        "relationships_and_intimacy",
        "growth_vector",
      ],
      sections: [
        [
          "core_pattern",
          "Ядро личности",
          "Первый абзац.\n\nВторой абзац.",
          "01 · ядро личности",
        ],
        [
          "perception_and_mind",
          "Мышление и восприятие",
          "Текст мышления.",
          "02 · мышление и восприятие",
        ],
        [
          "emotional_regulation",
          "Эмоциональная регуляция",
          "Текст эмоций.",
          "03 · эмоциональная регуляция",
        ],
        [
          "agency_and_desire",
          "Воля и действие",
          "Текст воли.",
          "04 · воля и действие",
        ],
        [
          "relationships_and_intimacy",
          "Близость и отношения",
          "Текст отношений.",
          "05 · близость и отношения",
        ],
        ["growth_vector", "Вектор роста", "Текст роста.", "06 · вектор роста"],
      ].map(([section_id, title, body, eyebrow]) => ({
        section_id,
        title,
        body,
        evidence_ids: ["ev:1"],
        covered_theme_ids: ["theme:1"],
        reader_display: {
          eyebrow,
          subtitle: "подзаголовок",
          aside_title: "в фокусе",
          aside_bullets: ["первое", "второе"],
        },
      })),
    },
    assembled_payload: {
      reader_view: {
        layout_order: ["hero", "narrative", "calculation_layer"],
        hero: {
          eyebrow: "Astrotype v2 · натальный отчёт",
          title: "Натальный портрет личности",
          status_label: "Полный отчёт готов",
          calculation_label: "Карта и расчёт ниже",
          pdf_label: "Предпросмотр PDF",
        },
      },
    },
  },
  progress: {
    status: "ready",
    total_segments: 6,
    ready_segments: 6,
    failed_segments: 0,
    running_segments: 0,
    segments: [],
  },
  outline: null,
  infographic: {
    id: "info-1",
    status: "ready",
    source_version: "v2.0",
    calculation_layer: {
      reader_blocks: [
        "key_indicators",
        "planet_positions",
        "balance_bars",
        "house_emphasis",
        "aspect_network",
        "key_aspects",
        "calculation_matrix",
      ],
      key_indicators: {
        ascendant: {
          body: "Ascendant",
          degree_label: "3.10° Scorpio",
          house_number: 1,
        },
        mc: { body: "MC", degree_label: "MC · Leo", house_number: 10 },
        ascendant_ruler: {
          planet: "Mars",
          position: { body: "Mars", degree_label: "19.40° Capricorn" },
        },
      },
      planet_positions: [
        {
          body: "Sun",
          sign: "Aries",
          house_number: 1,
          sign_degree: 15.2,
          degree_label: "15.20° Aries",
          retrograde: false,
          sampled_aspects: [
            {
              body_a: "Sun",
              body_b: "Moon",
              aspect_code: "square",
              orb_degrees: 2.1,
            },
          ],
        },
      ],
      balance_bars: {
        elements: [{ category: "elements", key: "fire", value: 34, rank: 1 }],
        modalities: [
          { category: "modalities", key: "cardinal", value: 42, rank: 1 },
        ],
      },
      house_emphasis: {
        bars: [
          { house_number: 1, sign: "Scorpio", body_count: 2, accent_weight: 2 },
        ],
        top_houses: [
          { house_number: 1, sign: "Scorpio", body_count: 2, accent_weight: 2 },
        ],
      },
      aspect_network: {
        nodes: [{ id: "Sun", label: "Sun" }],
        edges: [
          {
            source: "Sun",
            target: "Moon",
            aspect_code: "square",
            strength: 0.82,
          },
        ],
      },
      key_aspects: [
        {
          body_a: "Sun",
          body_b: "Moon",
          aspect_code: "square",
          orb_degrees: 2.1,
        },
      ],
      calculation_matrix: {
        house_mode: { angular: 2 },
        hemispheres: { upper: 1, lower: 1 },
        quadrants: { q1: 1 },
        aspect_profile: { counts: { tension: 1 } },
      },
    },
  },
  facts: [],
  segments: [],
};

const vm = buildV2ReportReaderViewModel(samplePayload);

assert.equal(vm.hero.eyebrow, "Astrotype v2 · натальный отчёт");
assert.deepEqual(vm.layoutOrder, ["hero", "narrative", "calculation_layer"]);
assert.deepEqual(
  vm.sections.map((section) => section.title),
  [
    "Ядро личности",
    "Мышление и восприятие",
    "Эмоциональная регуляция",
    "Воля и действие",
    "Близость и отношения",
    "Вектор роста",
  ],
);
assert.deepEqual(
  vm.sections.map((section) => section.eyebrow),
  [
    "01 · ядро личности",
    "02 · мышление и восприятие",
    "03 · эмоциональная регуляция",
    "04 · воля и действие",
    "05 · близость и отношения",
    "06 · вектор роста",
  ],
);
assert.deepEqual(vm.sections[0].paragraphs, ["Первый абзац.", "Второй абзац."]);
assert.equal(
  vm.calculationLayer.keyIndicators.ascendant?.degreeLabel,
  "3.10° Scorpio",
);
assert.equal(
  vm.calculationLayer.planetPositions[0].sampledAspects[0].aspectCode,
  "square",
);
assert.equal(vm.calculationLayer.balanceBars.elements[0].label, "fire");
assert.equal(vm.calculationLayer.houseEmphasis.bars[0].houseNumber, 1);
assert.equal(vm.calculationLayer.aspectNetwork.edges[0].source, "Sun");
assert.equal(vm.calculationLayer.keyAspects[0].orbDegrees, 2.1);
assert.equal(vm.calculationLayer.calculationMatrix.houseMode.angular, 2);

const vmText = JSON.stringify(vm).toLowerCase();
for (const forbidden of [
  "socionics",
  "model a",
  "function_strengths",
  "mbti",
]) {
  assert.equal(
    vmText.includes(forbidden),
    false,
    `forbidden marker leaked: ${forbidden}`,
  );
}

console.log("V2 report view-model contract OK");
