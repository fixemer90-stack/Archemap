import { api } from "@/lib/api-client";

export interface AstrotypeV2GenerationResponse {
  contract_version: "astrotype_v2_generation_job_v1";
  status: "queued" | "already_exists" | string;
  profile_id: string;
  report_id?: string;
  generation_id?: string;
  links?: {
    report?: string;
    progress?: string;
  };
}

export interface AstrotypeV2ProgressResponse {
  contract_version: "astrotype_v2_report_progress_v1";
  report_id: string;
  chart_id: string;
  status: string;
  total_segments: number;
  ready_segments: number;
  failed_segments: number;
  running_segments: number;
  segments: Array<{
    section_key: string;
    status: string;
    provider: string | null;
    model: string | null;
    prompt_version: string | null;
    error: string | null;
  }>;
}

export interface AstrotypeV2ReportResponse {
  contract_version: "astrotype_v2_report_api_v1";
  report: {
    id: string;
    chart_id: string;
    status: string;
    version: number;
    deterministic_payload: Record<string, unknown> | null;
    narrative_payload: Record<string, unknown> | null;
    assembled_payload: Record<string, unknown> | null;
  };
  progress: AstrotypeV2ProgressResponse;
  outline: Record<string, unknown> | null;
  infographic: {
    id: string;
    status: string;
    source_version: string;
    calculation_layer: Record<string, unknown>;
  } | null;
  facts: Array<Record<string, unknown>>;
  segments: Array<{
    section_key: string;
    status: string;
    payload: Record<string, unknown> | null;
    error: string | null;
  }>;
}

export function generateAstrotypeV2Report(
  profileId: string,
  force = false,
): Promise<AstrotypeV2GenerationResponse> {
  return api.post<AstrotypeV2GenerationResponse>("/api/v1/astrotype-v2/reports", {
    profile_id: profileId,
    force,
  });
}

export function fetchAstrotypeV2Report(
  reportId: string,
): Promise<AstrotypeV2ReportResponse> {
  return api.get<AstrotypeV2ReportResponse>(
    `/api/v1/astrotype-v2/reports/${reportId}`,
  );
}

export function fetchAstrotypeV2Progress(
  reportId: string,
): Promise<AstrotypeV2ProgressResponse> {
  return api.get<AstrotypeV2ProgressResponse>(
    `/api/v1/astrotype-v2/reports/${reportId}/progress`,
  );
}
