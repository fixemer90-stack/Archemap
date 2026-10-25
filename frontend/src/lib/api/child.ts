import { apiClient } from "@/lib/api-client";
import type {
  ChildGeneration,
  ChildQuestionnaire,
  ChildRecord,
  ChildReport,
} from "@/types/child";

const root = "/api/v1/child";
const id = encodeURIComponent;
export const newChildKey = (operation: string) =>
  `child-${operation}:${crypto.randomUUID()}`;
export const listChildren = () =>
  apiClient<{ children: ChildRecord[] }>(`${root}/children`);
export const getChild = (childId: string) =>
  apiClient<ChildRecord>(`${root}/children/${id(childId)}`);
export const getChildQuestionnaire = (childId: string) =>
  apiClient<ChildQuestionnaire>(
    `${root}/children/${id(childId)}/questionnaires/current`,
  );
export const saveChildAnswers = (
  sessionId: string,
  answers: Record<string, string>,
) =>
  apiClient<ChildQuestionnaire>(
    `${root}/questionnaires/${id(sessionId)}/answers`,
    {
      method: "PUT",
      body: {
        answers: Object.entries(answers).map(([question_key, option]) => ({
          question_key,
          option,
        })),
      },
    },
  );
export const completeChildQuestionnaire = (sessionId: string, key: string) =>
  apiClient<ChildQuestionnaire>(
    `${root}/questionnaires/${id(sessionId)}/complete`,
    { method: "POST", body: {}, headers: { "Idempotency-Key": key } },
  );
export const createChildReport = (
  childId: string,
  sessionId: string,
  key: string,
) =>
  apiClient<ChildGeneration>(`${root}/reports`, {
    method: "POST",
    body: { child_profile_id: childId, questionnaire_session_id: sessionId },
    headers: { "Idempotency-Key": key },
  });
export const getChildGeneration = (generationId: string) =>
  apiClient<ChildGeneration>(`${root}/generations/${id(generationId)}`);
export const getChildReport = (reportId: string) =>
  apiClient<ChildReport>(`${root}/reports/${id(reportId)}`);
export const childPdfUrl = (reportId: string, snapshotId: string) =>
  `${root}/reports/${id(reportId)}/pdf?age_snapshot_id=${id(snapshotId)}`;
export const retryChildReport = (reportId: string, key: string) =>
  apiClient<ChildGeneration>(`${root}/reports/${id(reportId)}/regenerate`, {
    method: "POST",
    body: { scope: "failed_sections" },
    headers: { "Idempotency-Key": key },
  });
export const updateChildAge = (
  reportId: string,
  version: number,
  key: string,
) =>
  apiClient<ChildGeneration>(`${root}/reports/${id(reportId)}/age-updates`, {
    method: "POST",
    body: { expected_core_report_version: version },
    headers: { "Idempotency-Key": key },
  });
export const childTerminal = (status: string) =>
  [
    "ready",
    "narrative_failed",
    "failed",
    "age_update_ready",
    "age_update_failed",
    "child_narrative_disabled",
  ].includes(status);
