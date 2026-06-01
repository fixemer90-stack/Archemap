import { api } from "@/lib/api-client";
import type {
  ChartSnapshotApiResponse,
  ProfileApiResponse,
  ReportApiData,
} from "@/lib/report/view-model";

export async function fetchReportApiData(
  profileId: string,
  token?: string,
): Promise<ReportApiData> {
  const [profile, chartSnapshot] = await Promise.all([
    api.get<ProfileApiResponse>(`/api/v1/profiles/${profileId}`, token),
    api.post<ChartSnapshotApiResponse>(
      `/api/v1/profiles/${profileId}/chart`,
      {},
      token,
    ),
  ]);

  return { profile, chartSnapshot };
}
