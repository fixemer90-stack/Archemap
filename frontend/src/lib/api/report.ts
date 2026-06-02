import { api } from "@/lib/api-client";
import type {
  ChartSnapshotApiResponse,
  GeneratedReportApiResponse,
  ProfileApiResponse,
  ReportApiData,
} from "@/lib/report/view-model";

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
    product === "self"
      ? Promise.resolve(null)
      : api.get<{ items: GeneratedReportApiResponse[] }>(
          `/api/v1/reports?product=${encodeURIComponent(product)}&limit=100`,
          token,
        ),
  ]);

  const generatedReport = reportList?.items.find(
    (item) => item.profile_id === profileId && item.status === "ready",
  );

  return { profile, chartSnapshot, requestedProduct: product, generatedReport };
}
