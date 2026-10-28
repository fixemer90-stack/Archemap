import type { Page, Route } from "@playwright/test";

export const childFixture = (id: string, display_name: string) => ({
  id,
  display_name,
  relationship_type: "child",
  birth_date: "2021-05-12",
  birth_time: null,
  birth_time_confidence: "unknown",
  birth_place: {
    label: "Москва",
    latitude: 55.75,
    longitude: 37.61,
    timezone: "Europe/Moscow",
  },
  caregiver_context: {
    primary_caregiver: true,
    daily_contact: "high",
    boundary_role: "shared",
    soothing_role: "mostly_me",
  },
  age: {
    age_years: 5,
    age_months: 5,
    age_days: 12,
    age_stage: "3-6",
    as_of_date: "2026-10-24",
  },
});
export const childSectionManifest = [
  {
    key: "how_to_use",
    title: "Как читать этот отчёт",
  },
  {
    key: "parent_style",
    title: "Ваш стиль взаимодействия",
  },
  {
    key: "child_interaction_needs",
    title: "Что помогает ребёнку в контакте",
  },
  {
    key: "natural_contact",
    title: "Где контакт складывается естественно",
  },
  {
    key: "friction_zones",
    title: "Где может возникать напряжение",
  },
  {
    key: "soothing_support",
    title: "Как поддерживать и успокаивать",
  },
  {
    key: "boundaries_rules",
    title: "Границы и правила",
  },
  {
    key: "autonomy",
    title: "Самостоятельность",
  },
  {
    key: "explanation_learning",
    title: "Объяснения и обучение",
  },
  {
    key: "praise_recognition",
    title: "Похвала и признание",
  },
  {
    key: "conflict_cycle",
    title: "Цикл конфликта",
  },
  {
    key: "not_personal",
    title: "Что важно не принимать на свой счёт",
  },
  {
    key: "parent_strengths",
    title: "На что вы уже можете опереться",
  },
  {
    key: "conscious_adjustments",
    title: "Что можно настраивать осознанно",
  },
  {
    key: "current_age",
    title: "Что важно в текущем возрасте",
  },
];
export const childQuestions = [
  {
    key: "support",
    prompt: "Что помогает восстановить контакт?",
    required: true,
    options: [
      { code: "pause", label: "Спокойная пауза рядом" },
      { code: "talk", label: "Короткий разговор" },
    ],
  },
  {
    key: "boundaries",
    prompt: "Как вы договариваетесь о правилах?",
    required: true,
    options: [
      { code: "together", label: "Обсуждаем заранее" },
      { code: "later", label: "Возвращаемся позже" },
    ],
  },
];
export async function mockE22Child(
  page: Page,
  options: {
    access?: number;
    readerStatus?: string;
    readerQuality?: "ready" | "limited";
    poll?: boolean;
    ageFailure?: boolean;
  } = {},
) {
  const children = [
    childFixture("child-a", "Миша"),
    childFixture("child-b", "Саша"),
  ];
  const drafts: Record<string, Record<string, string>> = {
    "child-a": {},
    "child-b": { support: "talk" },
  };
  const completed = new Set<string>();
  const state = {
    children,
    drafts,
    writes: [] as string[],
    completions: 0,
    creates: [] as unknown[],
    keys: [] as string[],
    retryKeys: [] as string[],
    retryTransportFail: false,
    unhandled: [] as string[],
    generationReads: 0,
    reportReads: 0,
    expire: false,
    ageUpdated: false,
    ageGenerationReads: 0,
    ageRequests: [] as unknown[],
    lastCreate: null as Record<string, unknown> | null,
  };
  const respond = (r: Route, body: unknown, status = 200) =>
    r.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  const questionnaire = (id: string) => ({
    session_id: `session-${id}`,
    child_id: id,
    status: completed.has(id) ? "completed" : "draft",
    questionnaire_version: "child-questionnaire-v1",
    age_stage: "3-6",
    required_question_ids: ["support", "boundaries"],
    questions: childQuestions,
    answers: Object.entries(drafts[id] ?? {}).map(([question_key, option]) => ({
      question_key,
      option,
    })),
    missing_required: childQuestions
      .filter((q) => !drafts[id]?.[q.key])
      .map((q) => q.key),
  });
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname,
      method = req.method();
    if (path === "/api/v1/users/me")
      return respond(route, {
        id: "adult",
        name: "Алина",
        email: "not-a-display-name@example.test",
        is_active: true,
      });
    if (path === "/api/v1/billing/access")
      return respond(route, {
        account_tier: "plus",
        access_state: "plus_active",
        accessible_products: ["self"],
        entitlements: [],
        latest_payment: null,
      });
    if (path === "/api/v1/profiles/geocode")
      return respond(route, {
        items: [
          {
            display_name: "Москва, Россия",
            city: "Москва",
            country: "Россия",
            latitude: 55.75,
            longitude: 37.61,
            timezone: "Europe/Moscow",
            selection_token: "fixture-selection",
          },
        ],
      });
    if (path === "/api/v1/auth/refresh") return respond(route, {}, 401);
    if (!path.startsWith("/api/v1/child")) {
      state.unhandled.push(path);
      return respond(route, {}, 404);
    }
    if (state.expire) return respond(route, {}, 401);
    if (options.access)
      return respond(route, { detail: "unavailable" }, options.access);
    if (path === "/api/v1/child/children") {
      if (method === "POST") {
        const body = req.postDataJSON();
        state.lastCreate = body;
        state.keys.push(req.headers()["idempotency-key"]);
        const child = {
          ...childFixture("child-new", body.display_name),
          ...body,
        };
        children.push(child);
        drafts[child.id] = {};
        return respond(route, child, 201);
      }
      return respond(route, { children });
    }
    const child = path.match(/\/children\/([^/]+)$/);
    if (child) {
      const record = children.find((c) => c.id === child[1]);
      if (!record) return respond(route, {}, 404);
      if (method === "PATCH") Object.assign(record, req.postDataJSON());
      return respond(route, record);
    }
    const current = path.match(/\/children\/([^/]+)\/questionnaires\/current$/);
    if (current) return respond(route, questionnaire(current[1]));
    const session = path.match(
      /\/questionnaires\/session-([^/]+)\/(answers|complete)$/,
    );
    if (session) {
      const id = session[1];
      if (session[2] === "answers") {
        drafts[id] = Object.fromEntries(
          req
            .postDataJSON()
            .answers.map((answer: { question_key: string; option: string }) => [
              answer.question_key,
              answer.option,
            ]),
        );
        state.writes.push(id);
      } else {
        state.completions++;
        completed.add(id);
        state.keys.push(req.headers()["idempotency-key"]);
      }
      return respond(route, questionnaire(id));
    }
    if (path === "/api/v1/child/reports" && method === "POST") {
      state.creates.push(req.postDataJSON());
      state.keys.push(req.headers()["idempotency-key"]);
      return respond(
        route,
        {
          generation_id: "generation-a",
          report_id: null,
          status: "queued",
          poll_after_ms: 100,
        },
        202,
      );
    }
    if (path === "/api/v1/child/generations/generation-age") {
      state.ageGenerationReads++;
      state.ageUpdated = !options.ageFailure;
      return respond(route, {
        generation_id: "generation-age",
        child_id: "child-a",
        report_id: "report-a",
        operation: "age_update",
        status: options.ageFailure
          ? state.ageGenerationReads === 1
            ? "age_update_running"
            : "age_update_failed"
          : "age_update_ready",
      });
    }
    if (path === "/api/v1/child/generations/generation-a") {
      state.generationReads++;
      return respond(route, {
        child_id: "child-a",
        generation_id: "generation-a",
        report_id: "report-a",
        status:
          state.generationReads === 1
            ? "deterministic_ready"
            : (options.readerStatus ?? "narrative_failed"),
        poll_after_ms: 100,
      });
    }
    if (path === "/api/v1/child/reports/report-a") {
      state.reportReads++;
      const status =
        options.poll && state.generationReads < 2
          ? "deterministic_ready"
          : (options.readerStatus ?? "narrative_failed");
      return respond(route, {
        report_id: "report-a",
        child_id: "child-a",
        generation_id: "generation-a",
        status,
        presentation: {
          contract_version: "child_report_presentation_v1",
          title: "Как поддерживать контакт с ребёнком",
          introduction:
            "Этот отчёт — ориентир для взрослого, а не оценка ребёнка.",
          ...(options.readerQuality
            ? {
                quality: {
                  status: options.readerQuality,
                  reason_codes:
                    options.readerQuality === "limited"
                      ? ["cross_section_duplicate_prose"]
                      : [],
                  omitted_sections:
                    options.readerQuality === "limited" ? ["parent_style"] : [],
                  repeated_sections:
                    options.readerQuality === "limited"
                      ? ["how_to_use", "child_interaction_needs"]
                      : [],
                },
              }
            : {}),
          metadata: {
            core_report_version: 1,
            age_snapshot_id: state.ageUpdated
              ? "age-updated-a"
              : "age-pinned-a",
            as_of_date: state.ageUpdated ? "2026-10-24" : "2026-10-14",
          },
          sections: childSectionManifest.map((section, i) => ({
            ...section,
            status:
              state.ageUpdated && i === 14
                ? "deterministic_ready"
                : i === 2 && status !== "ready"
                  ? "pending"
                  : "ready",
            confidence_note:
              "Проверьте в повседневном общении; это не оценка ребёнка.",
            actions: [
              "Предложите небольшой выбор и оставьте время для ответа.",
            ],
            body:
              state.ageUpdated && i === 14
                ? null
                : i === 2 && status !== "ready"
                  ? null
                  : i === 0
                    ? "Начните с наблюдения за контактом. Попробуйте спокойную паузу рядом."
                    : i === 14
                      ? "На этом этапе попробуйте заранее обсудить переход к новому занятию."
                      : `Сохранённое пояснение ${i + 1}. Предложите ребёнку небольшой выбор.`,
          })),
          age: {
            stale: !state.ageUpdated,
            guidance_version: null,
            as_of_date: state.ageUpdated ? "2026-10-24" : "2026-10-14",
            age_snapshot_id: state.ageUpdated
              ? "age-updated-a"
              : "age-pinned-a",
            age_years: 5,
            age_months: 5,
            age_days: state.ageUpdated ? 12 : 2,
            age_stage: "3-6",
            body: "На этом этапе попробуйте заранее обсудить переход к новому занятию.",
          },
          technical_basis: {
            note: "Сохранённые расчёты и наблюдения помогают проверить основания рекомендаций.",
            confidence_markers: [
              {
                fact_id: "fact-one",
                level: "low",
                required_language: "conditional",
              },
            ],
          },
        },
      });
    }
    if (path.endsWith("/age-updates")) {
      state.ageRequests.push(req.postDataJSON());
      return respond(
        route,
        {
          generation_id: "generation-age",
          report_id: "report-a",
          status: "age_update_queued",
        },
        202,
      );
    }
    if (path.endsWith("/regenerate")) {
      state.retryKeys.push(req.headers()["idempotency-key"]);
      if (state.retryTransportFail) {
        state.retryTransportFail = false;
        return route.abort("connectionreset");
      }
      return respond(
        route,
        {
          generation_id: "generation-a",
          report_id: "report-a",
          status: "queued",
        },
        202,
      );
    }
    state.unhandled.push(`${method} ${path}`);
    return respond(route, {}, 404);
  });
  return state;
}
