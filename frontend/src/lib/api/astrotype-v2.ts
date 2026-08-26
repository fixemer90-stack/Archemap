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
  profile: {
    id: string;
    name: string;
    birth_date: string;
    birth_time: string | null;
    birth_time_accuracy: string;
    birth_place: string;
    timezone: string;
    latitude: number;
    longitude: number;
  } | null;
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
  return api.post<AstrotypeV2GenerationResponse>(
    "/api/v1/astrotype-v2/reports",
    {
      profile_id: profileId,
      force,
    },
  );
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

export async function downloadAstrotypeV2ReportPdf(
  reportId: string,
): Promise<void> {
  const response = await fetch(`/api/v1/astrotype-v2/reports/${reportId}/pdf`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    let message = "Не удалось скачать PDF.";
    try {
      const data = (await response.json()) as { detail?: string };
      message = data.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  const contentType = response.headers.get("content-type") || "";
  const blob = await response.blob();

  if (blob.size === 0) {
    throw new Error("PDF пришёл пустым. Попробуйте ещё раз.");
  }

  if (!contentType.includes("application/pdf")) {
    const text = await blob.text();
    throw new Error(text || "Сервер вернул не PDF-файл.");
  }

  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = `astrotype-v2-report-${reportId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 30_000);
}
