import { apiClient } from "@/lib/api-client";

export type CareerAnswerValue = string | number | null;
export type CareerAnswers = Record<string, CareerAnswerValue>;

export interface CareerQuestion {
  key: string;
  domain: string;
  answer_type: "scale_1_5" | "choice" | "integer" | "bounded_text";
  required: boolean;
}

export interface CareerQuestionnaire {
  contract_version: "career_questionnaire_v1";
  session_id: string;
  career_profile_id: string;
  profile_id?: string;
  chart_id?: string;
  status: "draft" | "completed";
  questionnaire_version?: string;
  questions?: CareerQuestion[];
  answers: CareerAnswers;
  missing_required: string[];
}

export interface CareerGenerationAccepted {
  contract_version: "career_generation_job_v1";
  status: string;
  generation_id: string;
  report_id: string | null;
  links: Record<string, string>;
}

export interface CareerGenerationStatus {
  contract_version: "career_generation_status_v1";
  generation_id: string;
  report_id: string | null;
  status: string;
  deterministic_status: "pending" | "ready" | "failed";
  narrative_status:
    "pending" | "generating" | "partial_failure" | "failed" | "ready";
  progress: { total: number; ready: number; failed: number; running: number };
  sections: Array<{
    section_key: string;
    status: string;
    error: string | null;
  }>;
}

export interface CareerReportPayload {
  contract_version: "career_report_read_v1";
  report_id: string;
  generation_id: string;
  status: string;
  version: number;
  versions: Record<string, string>;
  deterministic_payload: Record<string, unknown>;
  sections: Array<Record<string, unknown>>;
  section_states: Array<{
    section_key: string;
    status: string;
    error: string | null;
  }>;
  assembled_payload: Record<string, unknown>;
}

export function getCurrentCareerQuestionnaire(profileId: string) {
  return apiClient<CareerQuestionnaire>(
    `/api/v1/career/questionnaires/current?profile_id=${encodeURIComponent(profileId)}`,
  );
}

export function saveCareerQuestionnaire(
  sessionId: string,
  answers: CareerAnswers,
) {
  return apiClient<CareerQuestionnaire>(
    `/api/v1/career/questionnaires/${sessionId}/answers`,
    { method: "PUT", body: { answers } },
  );
}

export function completeCareerQuestionnaire(
  sessionId: string,
  idempotencyKey: string,
) {
  return apiClient<CareerQuestionnaire>(
    `/api/v1/career/questionnaires/${sessionId}/complete`,
    {
      method: "POST",
      body: {},
      headers: { "Idempotency-Key": idempotencyKey },
    },
  );
}

export function createCareerReport(profileId: string, idempotencyKey: string) {
  return apiClient<CareerGenerationAccepted>("/api/v1/career/reports", {
    method: "POST",
    body: { profile_id: profileId },
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export function getCareerGeneration(generationId: string) {
  return apiClient<CareerGenerationStatus>(
    `/api/v1/career/generations/${generationId}`,
  );
}

export function getCareerReport(reportId: string) {
  return apiClient<CareerReportPayload>(
    `/api/v1/career/reports/${encodeURIComponent(reportId)}`,
  );
}

export function getCareerReportPdfUrl(reportId: string) {
  return `/api/v1/career/reports/${encodeURIComponent(reportId)}/pdf`;
}
