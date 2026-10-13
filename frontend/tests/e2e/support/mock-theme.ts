import type { Page, Route } from "@playwright/test";

import { mockCareerApi } from "./mock-career";

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

const v2ReadyReport = {
  contract_version: "astrotype_v2_report_api_v1",
  profile: {
    id: "profile-1",
    name: "Алина",
    birth_date: "1990-05-17",
    birth_time: "08:35:00",
    birth_time_accuracy: "exact",
    birth_place: "Москва, Россия",
    timezone: "Europe/Moscow",
    latitude: 55.7558,
    longitude: 37.6176,
  },
  report: {
    id: "v2-report-1",
    chart_id: "chart-1",
    status: "complete",
    version: 1,
    deterministic_payload: {},
    narrative_payload: {
      section_order: ["core_pattern"],
      sections: [
        {
          section_id: "core_pattern",
          title: "Ваш внутренний рисунок",
          body: "Вы соединяете внимательность к деталям с потребностью видеть целую картину.\n\nВ спокойной среде это помогает действовать последовательно и без лишней спешки.",
          reader_display: {
            eyebrow: "Главная тема",
            subtitle: "Как складывается общий ритм карты",
            aside_title: "В фокусе",
            aside_bullets: ["Цельность", "Наблюдательность"],
          },
          evidence_ids: [],
          covered_theme_ids: [],
        },
      ],
    },
    assembled_payload: {
      reader_view: {
        layout_order: ["hero", "narrative", "calculation_layer"],
        hero: {
          eyebrow: "Astrotype Signature",
          status_label: "Полный отчёт готов",
          calculation_label: "Карта и расчёт ниже",
          pdf_label: "Скачать PDF",
        },
      },
    },
  },
  progress: {
    contract_version: "astrotype_v2_report_progress_v1",
    report_id: "v2-report-1",
    chart_id: "chart-1",
    status: "complete",
    total_segments: 1,
    ready_segments: 1,
    failed_segments: 0,
    running_segments: 0,
    segments: [],
  },
  outline: null,
  infographic: {
    contract_version: "natal_infographic_data_v2",
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
        ascendant: { body: "Ascendant", sign: "Aquarius", degree_label: "12°" },
        sun: { body: "Sun", sign: "Sagittarius", degree_label: "25°" },
        moon: { body: "Moon", sign: "Cancer", degree_label: "8°" },
      },
      planet_positions: [
        {
          body: "Sun",
          sign: "Sagittarius",
          house_number: 11,
          sign_degree: 25,
          degree_label: "25°",
          retrograde: false,
          sampled_aspects: [],
        },
        {
          body: "Moon",
          sign: "Cancer",
          house_number: 6,
          sign_degree: 8,
          degree_label: "8°",
          retrograde: false,
          sampled_aspects: [],
        },
        {
          body: "North Node",
          sign: "Aquarius",
          house_number: 1,
          sign_degree: 4,
          degree_label: "4°",
          retrograde: true,
          sampled_aspects: [],
        },
      ],
      balance_bars: {
        elements: [
          { category: "elements", key: "fire", value: 0.5, rank: 1 },
          { category: "elements", key: "water", value: 0.333, rank: 2 },
          { category: "elements", key: "air", value: 0.167, rank: 3 },
          { category: "elements", key: "earth", value: 0, rank: 4 },
        ],
        modalities: [
          { category: "modalities", key: "mutable", value: 0.5, rank: 1 },
          { category: "modalities", key: "cardinal", value: 0.333, rank: 2 },
          { category: "modalities", key: "fixed", value: 0.167, rank: 3 },
        ],
      },
      house_emphasis: {
        bars: Array.from({ length: 12 }, (_, index) => ({
          house_number: index + 1,
          sign:
            index === 0 ? "Aquarius" : index === 8 ? "Sagittarius" : "Cancer",
          body_count: index === 3 ? 0 : Math.max(1, 4 - (index % 4)),
          accent_weight: index === 3 ? 0 : [4, 2, 1, 0][index % 4],
        })),
        top_houses: [],
      },
      aspect_network: {
        nodes: [
          { id: "Sun", label: "Sun", sign: "Sagittarius", house_number: 11 },
          { id: "Moon", label: "Moon", sign: "Cancer", house_number: 6 },
          {
            id: "Mercury",
            label: "Mercury",
            sign: "Sagittarius",
            house_number: 10,
          },
          { id: "Venus", label: "Venus", sign: "Aquarius", house_number: 1 },
          { id: "Mars", label: "Mars", sign: "Cancer", house_number: 6 },
          {
            id: "North Node",
            label: "North Node",
            sign: "Aquarius",
            house_number: 1,
          },
        ],
        edges: [
          ["Sun", "Moon", "trine", 0.98, 0.4],
          ["Sun", "Mercury", "conjunction", 0.94, 0.7],
          ["Moon", "Venus", "square", 0.91, 1.1],
          ["Mars", "North Node", "sextile", 0.88, 1.4],
          ["Mercury", "Venus", "opposition", 0.84, 1.8],
          ["Sun", "North Node", "sextile", 0.8, 2.1],
          ["Moon", "Mars", "conjunction", 0.76, 2.5],
          ["Venus", "Mars", "trine", 0.72, 2.8],
          ["Mercury", "North Node", "square", 0.68, 3.1],
          ["Sun", "Mars", "quincunx", 0.64, 3.4],
        ].map(([source, target, aspect_code, strength, orb_degrees]) => ({
          source,
          target,
          aspect_code,
          strength,
          orb_degrees,
          applying: true,
        })),
      },
      key_aspects: [
        ["Sun", "Moon", "trine", 0.98, 0.4],
        ["Sun", "Mercury", "conjunction", 0.94, 0.7],
        ["Moon", "Venus", "square", 0.91, 1.1],
        ["Mars", "North Node", "sextile", 0.88, 1.4],
        ["Mercury", "Venus", "opposition", 0.84, 1.8],
        ["Sun", "North Node", "sextile", 0.8, 2.1],
        ["Moon", "Mars", "conjunction", 0.76, 2.5],
        ["Venus", "Mars", "trine", 0.72, 2.8],
        ["Mercury", "North Node", "square", 0.68, 3.1],
        ["Sun", "Mars", "quincunx", 0.64, 3.4],
      ].map(([body_a, body_b, aspect_code, strength, orb_degrees]) => ({
        body_a,
        body_b,
        aspect_code,
        strength,
        orb_degrees,
        applying: true,
      })),
      calculation_matrix: {
        house_mode: { angular: 5, succedent: 2, cadent: 3 },
        hemispheres: { upper: 5, lower: 2, eastern: 4, western: 3 },
        quadrants: { q1: 5, q2: 2, q3: 1, q4: 2 },
        aspect_profile: {
          counts: { resource: 4, tension: 4, conjunction: 2 },
        },
      },
    },
  },
  facts: [],
  segments: [],
};

export async function mockThemeMatrixApi(page: Page) {
  await mockCareerApi(page);
  await page.route("**/birth-data-refinement-status", async (route) =>
    json(route, {
      profile_id: "profile-1",
      can_refine: true,
      last_refined_at: null,
      next_available_at: null,
      retry_after_seconds: 0,
    }),
  );
  await page.route("**/api/v1/astrotype-v2/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (
      path === "/api/v1/astrotype-v2/reports" &&
      request.method() === "POST"
    ) {
      const payload = request.postDataJSON() as { profile_id?: string };
      if (payload.profile_id === "profile-error") {
        return json(route, { detail: "Провайдер временно недоступен" }, 503);
      }
      if (payload.profile_id === "profile-loading") {
        return json(route, {
          contract_version: "astrotype_v2_generation_job_v1",
          status: "queued",
          profile_id: "profile-loading",
          generation_id: "v2-generation-loading",
          links: {
            progress:
              "/api/v1/astrotype-v2/reports/generations/v2-generation-loading",
          },
        });
      }
      return json(route, {
        contract_version: "astrotype_v2_generation_job_v1",
        status: "already_exists",
        profile_id: "profile-1",
        generation_id: "v2-generation-1",
        report_id: "v2-report-1",
        links: { report: "/api/v1/astrotype-v2/reports/v2-report-1" },
      });
    }
    if (path === "/api/v1/astrotype-v2/reports/v2-report-1") {
      return json(route, v2ReadyReport);
    }
    if (
      path === "/api/v1/astrotype-v2/reports/generations/v2-generation-loading"
    ) {
      return json(route, {
        contract_version: "astrotype_v2_generation_status_v1",
        generation_id: "v2-generation-loading",
        status: "queued",
        profile_id: "profile-loading",
        report_id: null,
        sections: [],
        diagnostics: {},
      });
    }
    return json(route, { detail: `Unhandled V2 theme mock: ${path}` }, 404);
  });
}

export async function setStoredTheme(page: Page, theme: "light" | "dark") {
  await page.addInitScript((storedTheme) => {
    localStorage.setItem("astrotype-theme", storedTheme);
  }, theme);
}
