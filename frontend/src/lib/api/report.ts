import { api } from "@/lib/api-client";
import type {
  ChartSnapshotApiResponse,
  ProfileApiResponse,
  ReportApiData,
} from "@/lib/report/view-model";

export type ReportStatus =
  | "pending"
  | "deterministic_ready"
  | "generating_narrative"
  | "ready"
  | "narrative_failed"
  | string;

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
  sections: Array<Record<string, unknown>>;
  career_cta: Record<string, unknown> | null;
  content: Record<string, unknown> | null;
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
    quality_warning?: string | null;
    [key: string]: unknown;
  };
  narrative: NarrativeApiResponse | null;
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
  token?: string,
  product = "self",
): Promise<ReportApiData> {
  const [profile, chartSnapshot, reportList] = await Promise.all([
    api.get<ProfileApiResponse>(`/api/v1/profiles/${profileId}`, token),
    api.post<ChartSnapshotApiResponse>(
      `/api/v1/profiles/${profileId}/chart`,
      {},
      token,
    ),
    api.get<{ items: GeneratedReportApiResponse[] }>(
      `/api/v1/reports?product=${encodeURIComponent(product)}&limit=100`,
      token,
    ),
  ]);

  return {
    profile,
    chartSnapshot,
    requestedProduct: product,
    generatedReport: pickLatestReport(reportList.items ?? [], profileId),
  };
}

export async function generateReportForProfile(
  profileId: string,
  token?: string,
  product = "self",
  mode = "full",
): Promise<GeneratedReportApiResponse> {
  return api.post<GeneratedReportApiResponse>(
    "/api/v1/reports/generate",
    {
      profile_id: profileId,
      product,
      mode,
    },
    token,
  );
}

export async function fetchReportById(
  reportId: string,
  token?: string,
): Promise<GeneratedReportApiResponse> {
  return api.get<GeneratedReportApiResponse>(
    `/api/v1/reports/${reportId}`,
    token,
  );
}

export async function regenerateReportNarrative(
  reportId: string,
  token?: string,
): Promise<GeneratedReportApiResponse> {
  return api.post<GeneratedReportApiResponse>(
    `/api/v1/reports/${reportId}/narrative/regenerate`,
    {},
    token,
  );
}
