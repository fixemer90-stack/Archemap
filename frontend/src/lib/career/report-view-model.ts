import type { CareerReportPayload } from "@/lib/api/career";

export const CAREER_SECTION_ORDER = [
  "professional_summary",
  "work_style",
  "strengths",
  "decision_making",
  "leadership_and_influence",
  "optimal_environment",
  "risk_environment",
  "career_archetypes",
  "role_families",
  "career_paths",
] as const;

const SECTION_TITLES: Record<string, string> = {
  professional_summary: "Ваш профессиональный профиль",
  work_style: "Как вы работаете",
  strengths: "Сильные стороны",
  decision_making: "Стиль принятия решений",
  leadership_and_influence: "Лидерство и влияние",
  optimal_environment: "Оптимальная рабочая среда",
  risk_environment: "Что может снижать эффективность",
  career_archetypes: "Профессиональные архетипы",
  role_families: "Подходящие типы ролей",
  career_paths: "Возможные карьерные траектории",
};

const DIMENSION_LABELS: Record<string, string> = {
  leadership: "Лидерство",
  analytical_thinking: "Аналитическое мышление",
  systems_thinking: "Системное мышление",
  communication: "Коммуникация",
  creativity: "Творческий подход",
  structure: "Структура",
  autonomy: "Самостоятельность",
  risk_tolerance: "Отношение к риску",
  people_orientation: "Ориентация на людей",
  innovation: "Новаторство",
  long_term_focus: "Долгосрочный фокус",
  execution: "Реализация",
};

const CATEGORY_LABELS: Record<string, string> = {
  strong_match: "Выраженное соответствие",
  possible_match: "Возможное соответствие",
  context_dependent: "Зависит от контекста",
};

const ROLE_FAMILY_LABELS: Record<string, string> = {
  architecture: "Архитектура систем",
  product: "Продуктовая работа",
  strategy: "Стратегия",
  analytics: "Аналитика",
  consulting: "Консалтинг",
  operations: "Операционная работа",
  research: "Исследования",
  management: "Управление",
  entrepreneurship: "Предпринимательство",
  visual_arts: "Изобразительное творчество",
  word_and_media: "Слово и медиа",
  performing_arts: "Исполнительские искусства",
  craft_and_manual_work: "Ремесло и ручная работа",
  practical_technology: "Практическая техника",
  care_and_service: "Забота и сервис",
  land_and_nature: "Земля и природа",
  sales_and_field_work: "Продажи и полевая работа",
};

const CONTEXT_LABELS: Record<string, string> = {
  "experience:senior": "Опыт: уверенный профессиональный уровень",
  "experience:mid": "Опыт: развивающийся профессиональный уровень",
  "experience:entry": "Опыт: начало профессионального пути",
  "current_activity:provided": "Текущая деятельность учтена",
  "change_goal:provided": "Цель изменений учтена",
  "constraints:provided": "Практические ограничения учтены",
};

const CONTRADICTION_LABELS: Record<string, string> = {
  leadership_without_people_management:
    "Способность вести за собой может не совпадать с желанием управлять людьми.",
};

const DIMENSION_EXPLANATION =
  "Выраженность рабочей тенденции; число не является оценкой «хорошо» или «плохо».";
const TECHNICAL_BASIS =
  "Отчёт собран из сохранённых расчётов, ответов и версий правил. Технический слой нужен для проверяемости и не заменяет профессиональную консультацию или реальный опыт.";

export interface CareerNarrativeBlock {
  kind: "narrative";
  key: string;
  title: string;
  status: "ready" | "failed" | "pending";
  body: string | null;
}

export interface CareerDimensionItem {
  key: string;
  label: string;
  score: number;
  confidence: number | null;
  confidence_label: string;
}

export interface CareerContradictionItem {
  key: string;
  label: string;
  fact_key: string;
  capability_score: number | null;
  motivation_score: number | null;
}

export interface CareerContextItem {
  key: string;
  label: string;
}

export interface CareerRoleItem {
  key: string;
  title: string;
  category: string;
  reasons: string[];
  examples: string[];
  example_label: string;
}

export type CareerPresentationBlock =
  | CareerNarrativeBlock
  | {
      kind: "dimensions";
      key: "dimensions";
      title: string;
      note: string;
      items: CareerDimensionItem[];
    }
  | {
      kind: "contradictions";
      key: "contradictions";
      title: string;
      items: CareerContradictionItem[];
    }
  | {
      kind: "context";
      key: "context";
      title: string;
      items: CareerContextItem[];
    }
  | {
      kind: "roles";
      key: "roles";
      title: string;
      items: CareerRoleItem[];
    }
  | {
      kind: "technical_basis";
      key: "technical_basis";
      title: string;
      body: string;
    };

export interface CareerReportPresentation {
  contract_version:
    "career_report_presentation_v1" | "career_report_presentation_v2";
  report_status: string;
  notice: {
    kind: "narrative_failed" | "deterministic_ready";
    title: string;
    body: string;
  } | null;
  blocks: CareerPresentationBlock[];
}

export interface CareerReportViewModel extends CareerReportPresentation {
  sections: CareerNarrativeBlock[];
  dimensions: CareerDimensionItem[];
  contradictions: CareerContradictionItem[];
  context: CareerContextItem[];
  roles: CareerRoleItem[];
  technicalBasis: Extract<CareerPresentationBlock, { kind: "technical_basis" }>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function records(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function humanize(value: string): string {
  const normalized = value.replaceAll("_", " ").replaceAll(":", ": ");
  return normalized
    ? normalized.charAt(0).toUpperCase() + normalized.slice(1).toLowerCase()
    : "";
}

function usesV2Presentation(deterministic: Record<string, unknown>): boolean {
  if (text(deterministic.contract_version) === "career_interpretation_facts_v2")
    return true;
  return records(deterministic.role_matches).some(
    (item) => text(item.catalog_version) === "career-role-catalog-2",
  );
}

function reportNotice(status: string): CareerReportPresentation["notice"] {
  if (status === "narrative_failed" || status === "partial_failure") {
    return {
      kind: "narrative_failed",
      title: "Часть пояснений временно недоступна.",
      body: "Базовый профиль, показатели и уже готовые разделы остаются доступными.",
    };
  }
  if (
    [
      "deterministic_ready",
      "generating_sections",
      "narrative_pending",
      "generating",
      "pending",
    ].includes(status)
  ) {
    return {
      kind: "deterministic_ready",
      title: "Пояснения ещё готовятся.",
      body: "Базовый профиль и показатели уже доступны; десять разделов будут заполняться по мере готовности.",
    };
  }
  return null;
}

export function buildCareerReportPresentation(
  payload: CareerReportPayload,
): CareerReportPresentation {
  const deterministic = isRecord(payload.deterministic_payload)
    ? payload.deterministic_payload
    : {};
  const useV2Presentation = usesV2Presentation(deterministic);
  const sectionByKey = new Map(
    records(payload.sections).map((section) => [
      text(section.section_key),
      section,
    ]),
  );
  const stateByKey = new Map(
    payload.section_states.map((state) => [state.section_key, state]),
  );

  const blocks: CareerPresentationBlock[] = CAREER_SECTION_ORDER.map((key) => {
    const section = sectionByKey.get(key);
    const state = stateByKey.get(key);
    const body = text(section?.body);
    const sourceStatus = text(state?.status);
    const status: CareerNarrativeBlock["status"] = body
      ? "ready"
      : sourceStatus === "failed"
        ? "failed"
        : "pending";
    return {
      kind: "narrative",
      key,
      title: text(section?.title, SECTION_TITLES[key]),
      status,
      body: body || null,
    };
  });

  blocks.push({
    kind: "dimensions",
    key: "dimensions",
    title: "Выраженные рабочие тенденции",
    note: DIMENSION_EXPLANATION,
    items: records(deterministic.top_dimensions).map((item) => {
      const key = text(item.dimension);
      const confidence = numberOrNull(item.confidence);
      return {
        key,
        label: DIMENSION_LABELS[key] ?? humanize(key),
        score: numberOrNull(item.score) ?? 0,
        confidence,
        confidence_label:
          confidence !== null && confidence >= 0.75
            ? "Основания согласованы"
            : "Лучше проверить на опыте",
      };
    }),
  });

  const contradictionItems: CareerContradictionItem[] = records(
    deterministic.contradictions,
  ).map((item) => {
    const key = text(item.code, "contextual_tension");
    return {
      key,
      label:
        CONTRADICTION_LABELS[key] ??
        "Способность и мотивация могут проявляться по-разному; проверьте вывод в контексте реальной роли.",
      fact_key: text(item.fact_key),
      capability_score: numberOrNull(item.capability_score),
      motivation_score: numberOrNull(item.motivation_score),
    };
  });

  if (contradictionItems.length > 0) {
    blocks.push({
      kind: "contradictions",
      key: "contradictions",
      title: "Полезные развилки",
      items: contradictionItems,
    });
  }

  blocks.push({
    kind: "context",
    key: "context",
    title: "Учтённый контекст",
    items: strings(deterministic.context_constraints).map((key) => ({
      key,
      label: CONTEXT_LABELS[key] ?? humanize(key),
    })),
  });

  blocks.push({
    kind: "roles",
    key: "roles",
    title: "Семейства ролей",
    items: records(deterministic.role_matches).map((item) => {
      const key = text(item.role_family_key, "context_dependent");
      return {
        key,
        title: useV2Presentation
          ? (ROLE_FAMILY_LABELS[key] ?? humanize(key))
          : humanize(key),
        category:
          CATEGORY_LABELS[text(item.category)] ?? "Зависит от контекста",
        reasons: strings(item.reasons).map(humanize),
        examples: strings(item.profession_examples),
        example_label: "Возможный пример, а не назначение",
      };
    }),
  });

  blocks.push({
    kind: "technical_basis",
    key: "technical_basis",
    title: "Основа интерпретации",
    body: TECHNICAL_BASIS,
  });

  return {
    contract_version: useV2Presentation
      ? "career_report_presentation_v2"
      : "career_report_presentation_v1",
    report_status: text(payload.status, "pending"),
    notice: reportNotice(text(payload.status, "pending")),
    blocks,
  };
}

export function buildCareerReportViewModel(
  payload: CareerReportPayload,
): CareerReportViewModel {
  const presentation = buildCareerReportPresentation(payload);
  const section = <Kind extends CareerPresentationBlock["kind"]>(kind: Kind) =>
    presentation.blocks.find(
      (block): block is Extract<CareerPresentationBlock, { kind: Kind }> =>
        block.kind === kind,
    );

  return {
    ...presentation,
    sections: presentation.blocks.filter(
      (block): block is CareerNarrativeBlock => block.kind === "narrative",
    ),
    dimensions: section("dimensions")?.items ?? [],
    contradictions: section("contradictions")?.items ?? [],
    context: section("context")?.items ?? [],
    roles: section("roles")?.items ?? [],
    technicalBasis: section("technical_basis")!,
  };
}
