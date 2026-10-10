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
  infographic: null,
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
