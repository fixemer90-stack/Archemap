export const careerQuestions = [
  {
    key: "leadership_responsibility",
    domain: "leadership",
    answer_type: "scale_1_5",
    required: true,
  },
  {
    key: "people_management_motivation",
    domain: "leadership",
    answer_type: "scale_1_5",
    required: true,
  },
  {
    key: "autonomy_importance",
    domain: "autonomy",
    answer_type: "scale_1_5",
    required: true,
  },
  {
    key: "risk_preference",
    domain: "risk",
    answer_type: "choice",
    required: true,
  },
  {
    key: "preferred_track",
    domain: "track",
    answer_type: "choice",
    required: true,
  },
  {
    key: "current_activity",
    domain: "context",
    answer_type: "bounded_text",
    required: true,
  },
  {
    key: "experience_years",
    domain: "context",
    answer_type: "integer",
    required: true,
  },
  {
    key: "change_goal",
    domain: "context",
    answer_type: "bounded_text",
    required: true,
  },
  {
    key: "collaboration_preference",
    domain: "people",
    answer_type: "scale_1_5",
    required: true,
  },
  {
    key: "current_constraints",
    domain: "context",
    answer_type: "bounded_text",
    required: true,
  },
] as const;

export const sectionKeys = [
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

export const reportPayload = {
  contract_version: "career_report_read_v1",
  report_id: "report-1",
  generation_id: "generation-1",
  status: "ready",
  version: 1,
  versions: { scoring: "career-scoring-v1", prompt: "career-prompt-v1" },
  deterministic_payload: {
    top_dimensions: [
      { dimension: "systems_thinking", score: 88, confidence: 0.84 },
      { dimension: "autonomy", score: 81, confidence: 0.78 },
      { dimension: "leadership", score: 74, confidence: 0.7 },
    ],
    contradictions: [
      { code: "leadership_without_people_management", capability_score: 82 },
    ],
    context_constraints: ["experience:senior", "constraints:provided"],
    role_matches: [
      {
        role_family_key: "architecture",
        category: "strong_match",
        profession_examples: ["Solution Architect", "Системный аналитик"],
        reasons: ["dimension:systems_thinking"],
      },
    ],
  },
  sections: sectionKeys.map((sectionKey, index) => ({
    section_key: sectionKey,
    title: `Раздел ${index + 1}`,
    body: "Вы соединяете детали в целостную систему и лучше всего работаете там, где можно видеть причины, ограничения и последствия решений.\n\nПрактический вывод сохраняет контекст и не превращает склонность в предписание профессии.",
  })),
  section_states: sectionKeys.map((sectionKey) => ({
    section_key: sectionKey,
    status: "ready",
    error: null,
  })),
  assembled_payload: {},
};
