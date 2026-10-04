import { apiClient } from "@/lib/api-client";

export interface BirthProfile {
  id: string;
  user_id: string;
  name: string;
  birth_date: string;
  birth_time: string | null;
  birth_time_accuracy: "exact" | "approximate" | "unknown";
  birth_place: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

export interface BirthProfileList {
  items: BirthProfile[];
  total: number;
}

export interface RefinementAvailability {
  profile_id: string;
  can_refine: boolean;
  last_refined_at: string | null;
  next_available_at: string | null;
  retry_after_seconds: number;
}

export interface GeocodeSuggestion {
  display_name: string;
  latitude: number;
  longitude: number;
  city: string;
  country: string;
  timezone: string;
  selection_token: string;
}

export interface RefinementAccepted {
  revision_id: string;
  profile_id: string;
  changed_fields: string[];
  status: "queued";
  next_available_at: string;
}

export interface RefinementProgress {
  revision_id: string;
  profile_id: string;
  changed_fields: string[];
  status: "queued" | "processing" | "deterministic_ready" | "ready" | "failed";
  chart_id: string | null;
  report_id: string | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface RefinementPayload {
  birth_time: string | null;
  birth_time_accuracy: "exact" | "approximate" | "unknown";
  birth_place: string;
  latitude: number;
  longitude: number;
  timezone: string;
  geocode_selection_token?: string | null;
}

export function getBirthProfiles() {
  return apiClient<BirthProfileList>("/api/v1/profiles");
}

export function getRefinementAvailability(profileId: string) {
  return apiClient<RefinementAvailability>(
    `/api/v1/profiles/${encodeURIComponent(profileId)}/birth-data-refinement-status`,
  );
}

export function searchBirthPlaces(query: string) {
  return apiClient<{ items: GeocodeSuggestion[] }>(
    `/api/v1/profiles/geocode?q=${encodeURIComponent(query)}`,
  );
}

export function createBirthDataRefinement(
  profileId: string,
  payload: RefinementPayload,
  idempotencyKey: string,
) {
  return apiClient<RefinementAccepted>(
    `/api/v1/profiles/${encodeURIComponent(profileId)}/birth-data-refinements`,
    {
      method: "POST",
      body: payload,
      headers: { "Idempotency-Key": idempotencyKey },
    },
  );
}

export function getBirthDataRefinement(profileId: string, revisionId: string) {
  return apiClient<RefinementProgress>(
    `/api/v1/profiles/${encodeURIComponent(profileId)}/birth-data-refinements/${encodeURIComponent(revisionId)}`,
  );
}
