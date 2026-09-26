import type { Page, Route } from "@playwright/test";

import { careerQuestions, reportPayload } from "../fixtures/career";

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

export type CareerMockState = {
  answerWrites: number;
  completions: number;
  reportCreates: number;
  completionKeys: string[];
  reportKeys: string[];
};

export async function mockCareerApi(page: Page): Promise<CareerMockState> {
  await page.addInitScript(() => {
    if (!globalThis.crypto.randomUUID) {
      Object.defineProperty(globalThis.crypto, "randomUUID", {
        configurable: true,
        value: () => "00000000-0000-4000-8000-000000000001",
      });
    }
  });

  const state: CareerMockState = {
    answerWrites: 0,
    completions: 0,
    reportCreates: 0,
    completionKeys: [],
    reportKeys: [],
  };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/v1/users/me") {
      return json(route, {
        id: "user-1",
        email: "alina@example.com",
        name: "Алина",
        is_active: true,
      });
    }
    if (path === "/api/v1/billing/access") {
      return json(route, {
        account_tier: "plus",
        access_state: "plus_active",
        entitlements: [],
        latest_payment: null,
      });
    }
    if (path === "/api/v1/profiles") {
      return json(route, {
        items: [
          {
            id: "profile-1",
            name: "Алина",
            birth_date: "1990-05-17",
            birth_place: "Москва",
          },
        ],
      });
    }
    if (path === "/api/v1/career/questionnaires/current") {
      return json(route, {
        contract_version: "career_questionnaire_v1",
        session_id: "session-1",
        career_profile_id: "career-profile-1",
        profile_id: "profile-1",
        status: "draft",
        questionnaire_version: "career-questions-v1",
        questions: careerQuestions,
        answers: {},
        missing_required: careerQuestions.map((question) => question.key),
      });
    }
    if (
      path === "/api/v1/career/questionnaires/session-1/answers" &&
      request.method() === "PUT"
    ) {
      state.answerWrites += 1;
      const body = request.postDataJSON() as {
        answers: Record<string, unknown>;
      };
      return json(route, {
        contract_version: "career_questionnaire_v1",
        session_id: "session-1",
        career_profile_id: "career-profile-1",
        status: "draft",
        questions: careerQuestions,
        answers: body.answers,
        missing_required: [],
      });
    }
    if (
      path === "/api/v1/career/questionnaires/session-1/complete" &&
      request.method() === "POST"
    ) {
      state.completions += 1;
      state.completionKeys.push(request.headers()["idempotency-key"] ?? "");
      return json(route, {
        contract_version: "career_questionnaire_v1",
        session_id: "session-1",
        career_profile_id: "career-profile-1",
        status: "completed",
        questions: careerQuestions,
        answers: {},
        missing_required: [],
      });
    }
    if (path === "/api/v1/career/reports" && request.method() === "POST") {
      state.reportCreates += 1;
      state.reportKeys.push(request.headers()["idempotency-key"] ?? "");
      return json(route, {
        contract_version: "career_generation_job_v1",
        status: "queued",
        generation_id: "generation-1",
        report_id: null,
        links: {},
      });
    }
    if (path === "/api/v1/career/generations/generation-1") {
      return json(route, {
        contract_version: "career_generation_status_v1",
        generation_id: "generation-1",
        report_id: "report-1",
        status: "deterministic_ready",
        deterministic_status: "ready",
        narrative_status: "generating",
        progress: { total: 10, ready: 3, failed: 0, running: 1 },
        sections: [],
      });
    }
    if (path === "/api/v1/career/reports/report-1") {
      return json(route, reportPayload);
    }
    if (path === "/api/v1/career/reports/report-1/pdf") {
      return route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: Buffer.from("%PDF-1.7 mocked-download"),
      });
    }

    return json(
      route,
      { detail: `Unhandled mock route: ${request.method()} ${path}` },
      404,
    );
  });

  return state;
}
