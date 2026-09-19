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

const CONTEXT_LABELS: Record<string, string> = {
  "experience:senior": "Уверенный профессиональный опыт",
  "experience:mid": "Развивающийся профессиональный опыт",
  "experience:entry": "Начало профессионального пути",
  "current_activity:provided": "Текущая деятельность учтена",
  "change_goal:provided": "Цель изменений учтена",
  "constraints:provided": "Практические ограничения учтены",
};

export interface CareerReportViewModel {
  status: string;
  sections: Array<{
    key: string;
    title: string;
    body: string | null;
    status: string;
  }>;
  dimensions: Array<{
    key: string;
    label: string;
    score: number;
    confidence: number | null;
    explanation: string;
  }>;
  contradictions: string[];
  context: string[];
  roles: Array<{
    key: string;
    title: string;
    category: string;
    reasons: string[];
    examples: string[];
    exampleLabel: string;
  }>;
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

export function buildCareerReportViewModel(
  payload: CareerReportPayload,
): CareerReportViewModel {
  const deterministic = payload.deterministic_payload;
  const sectionByKey = new Map(
    payload.sections
      .filter(isRecord)
      .map((section) => [text(section.section_key), section] as const),
  );
  const stateByKey = new Map(
    payload.section_states.map((state) => [state.section_key, state]),
  );

  const sections = CAREER_SECTION_ORDER.map((key) => {
    const section = sectionByKey.get(key);
    const state = stateByKey.get(key);
    return {
      key,
      title: text(section?.title, SECTION_TITLES[key]),
      body: section ? text(section.body) || null : null,
      status: state?.status ?? (section ? "ready" : "pending"),
    };
  });

  const dimensions = records(deterministic.top_dimensions).map((item) => {
    const key = text(item.dimension);
    return {
      key,
      label: DIMENSION_LABELS[key] ?? key.replaceAll("_", " "),
      score: typeof item.score === "number" ? item.score : 0,
      confidence: typeof item.confidence === "number" ? item.confidence : null,
      explanation:
        "Выраженность рабочей тенденции — не оценка личности как «хорошей» или «плохой».",
    };
  });

  const contradictions = records(deterministic.contradictions).map(
    () =>
      "Здесь способность и личная мотивация могут расходиться. Это не ошибка, а полезная развилка для выбора формата роли.",
  );

  const context = strings(deterministic.context_constraints)
    .map((key) => CONTEXT_LABELS[key])
    .filter((item): item is string => Boolean(item));

  const roles = records(deterministic.role_matches).map((item) => {
    const key = text(item.role_family_key);
    return {
      key,
      title: key.replaceAll("_", " "),
      category: CATEGORY_LABELS[text(item.category)] ?? "Зависит от контекста",
      reasons: strings(item.reasons).map((reason) =>
        reason.replaceAll("_", " ").replaceAll(":", ": "),
      ),
      examples: strings(item.profession_examples),
      exampleLabel: "Возможный пример, а не назначение",
    };
  });

  return {
    status: payload.status,
    sections,
    dimensions,
    contradictions,
    context,
    roles,
  };
}
