export type BirthTimeConfidence = "exact" | "approximate" | "unknown";
export interface ChildAge {
  age_years: number;
  age_months: number;
  age_days: number;
  age_stage: string;
  as_of_date: string;
}
export interface ChildRecord {
  id: string;
  display_name: string;
  relationship_type: string;
  birth_date: string;
  birth_time: string | null;
  birth_time_confidence: BirthTimeConfidence;
  birth_place: {
    label: string;
    latitude: number;
    longitude: number;
    timezone: string;
  };
  caregiver_context: Record<string, string | boolean>;
  age: ChildAge;
}
export interface ChildQuestionnaire {
  session_id: string;
  child_id: string;
  status: "draft" | "completed";
  questionnaire_version: string;
  age_stage: string;
  required_question_ids: string[];
  missing_required: string[];
  questions: Array<{
    key: string;
    prompt: string;
    required: boolean;
    options: Array<{ code: string; label: string }>;
  }>;
  answers: Array<{ question_key: string; option: string }>;
}
export interface ChildGeneration {
  child_id?: string;
  generation_id: string;
  report_id: string | null;
  status: string;
  poll_after_ms?: number;
}
export interface ChildPresentation {
  contract_version: "child_report_presentation_v1";
  title: string;
  introduction: string;
  metadata: {
    core_report_version: number;
    age_snapshot_id: string;
    as_of_date: string;
  };
  sections: Array<{
    key: string;
    title: string;
    status: string;
    body: string | null;
    actions: string[];
    confidence_note: string;
  }>;
  age: ChildAge & {
    age_snapshot_id: string;
    stale: boolean;
    guidance_version: number | null;
  };
  technical_basis: {
    note: string;
    confidence_markers: Array<{
      fact_id: string;
      level: string;
      required_language: string;
    }>;
  };
}
export interface ChildReport {
  report_id: string;
  child_id: string;
  generation_id: string;
  status: string;
  presentation: ChildPresentation | null;
}
