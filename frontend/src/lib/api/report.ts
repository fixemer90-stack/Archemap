import { api } from "@/lib/api-client";
import type {
  ChartSnapshotApiResponse,
  FunctionStrengths,
  ProfileApiResponse,
  ReportApiData,
  ReportSocionicsData,
} from "@/lib/report/view-model";

export type ReportStatus =
  | "pending"
  | "deterministic_ready"
  | "generating_narrative"
  | "ready"
  | "narrative_failed"
  | string;

export type NarrativeStageId =
  | "plan"
  | "identity"
  | "emotional"
  | "relationships"
  | "development"
  | "house_scenarios"
  | "assembly"
  | string;

export interface NarrativeStageProgressApiResponse {
  total_stages: number;
  completed_stages: number;
  current_stage?: NarrativeStageId | null;
  running_stage?: NarrativeStageId | null;
  failed_stage?: NarrativeStageId | null;
  ready: boolean;
  stages?: NarrativeStageArtifactApiResponse[];
}

export interface NarrativeStageArtifactApiResponse {
  stage_id: NarrativeStageId;
  status: string;
  prompt_version: string;
  model_name: string;
  input_hash: string;
  attempt_count: number;
  error_message: string | null;
  artifact: Record<string, unknown> | null;
}

export interface NarrativeApiResponse {
  id: string;
  report_id: string;
  product: string;
  prompt_version: string;
  model_provider: string;
  model_name: string;
  status: string;
  title: string | null;
  hero: Record<string, unknown> | null;
  dominants: Array<Record<string, unknown>>;
  inner_mechanism: Record<string, unknown> | null;
  house_scenarios: Array<Record<string, unknown>>;
  calibration_questions: Array<Record<string, unknown>>;
  contradictions: Array<Record<string, unknown>>;
  failure_modes: Array<Record<string, unknown>>;
  maturity_levels: Record<string, unknown> | null;
  sections: Array<Record<string, unknown>>;
  career_cta: Record<string, unknown> | null;
  content: Record<string, unknown> | null;
  stage_progress: NarrativeStageProgressApiResponse | null;
  stage_artifacts: NarrativeStageArtifactApiResponse[];
  error_message: string | null;
  generation_started_at: string | null;
  generation_finished_at: string | null;
  generation_attempts: number;
  created_at: string;
  updated_at: string;
}

export interface GeneratedReportApiResponse {
  id: string;
  profile_id: string;
  product: string;
  version: number;
  status: ReportStatus;
  mode: string;
  archetype: string | null;
  score: number | null;
  confidence: number | null;
  pdf_url?: string | null;
  pdf_generated?: boolean;
  report_data: {
    product?: string;
    archetype?: {
      primary?: string;
      score?: number;
      confidence?: {
        value: number;
        label: string;
        reason_codes: string[];
      };
    };
    claims?: Array<{
      claim_id: string;
      section: string;
      archetype: string;
      score: number;
      confidence: {
        value: number;
        label: string;
        reason_codes: string[];
      };
      message: string;
    }>;
    all_archetype_scores?: Record<string, number>;
    socionics?: Partial<ReportSocionicsData>;
    function_strengths?: Partial<FunctionStrengths>;
    quality_warning?: string | null;
    [key: string]: unknown;
  };
  narrative: NarrativeApiResponse | null;
  narrative_progress?: NarrativeStageProgressApiResponse | null;
  narrative_stage_artifacts?: NarrativeStageArtifactApiResponse[];
  error_message?: string | null;
  created_at?: string;
  updated_at?: string;
}

function pickLatestReport(
  reports: GeneratedReportApiResponse[],
  profileId: string,
): GeneratedReportApiResponse | undefined {
  return reports
    .filter((item) => item.profile_id === profileId)
    .sort((a, b) => b.version - a.version)[0];
}

export async function fetchReportApiData(
  profileId: string,
  product = "self",
): Promise<ReportApiData> {
  const [profile, chartSnapshot, reportList] = await Promise.all([
    api.get<ProfileApiResponse>(`/api/v1/profiles/${profileId}`),
    api.post<ChartSnapshotApiResponse>(
      `/api/v1/profiles/${profileId}/chart`,
      {},
    ),
    api.get<{ items: GeneratedReportApiResponse[] }>(
      `/api/v1/reports?product=${encodeURIComponent(product)}&limit=100`,
    ),
  ]);

  const latestReport = pickLatestReport(reportList.items ?? [], profileId);
  const generatedReport = latestReport
    ? await fetchReportById(latestReport.id)
    : undefined;

  return {
    profile,
    chartSnapshot,
    requestedProduct: product,
    generatedReport,
  };
}

export async function generateReportForProfile(
  profileId: string,
  product = "self",
  mode = "full",
): Promise<GeneratedReportApiResponse> {
  return api.post<GeneratedReportApiResponse>("/api/v1/reports/generate", {
    profile_id: profileId,
    product,
    mode,
  });
}

export async function fetchReportById(
  reportId: string,
): Promise<GeneratedReportApiResponse> {
  return api.get<GeneratedReportApiResponse>(`/api/v1/reports/${reportId}`);
}

export async function regenerateReportNarrative(
  reportId: string,
): Promise<GeneratedReportApiResponse> {
  return api.post<GeneratedReportApiResponse>(
    `/api/v1/reports/${reportId}/narrative/regenerate`,
    {},
  );
}
