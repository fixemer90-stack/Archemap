"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";

export function useApiQuery<T>(
  key: string[],
  endpoint: string,
  options?: Omit<UseQueryOptions<T, ApiError>, "queryKey" | "queryFn">,
) {
  return useQuery<T, ApiError>({
    queryKey: key,
    queryFn: () => api.get<T>(endpoint),
    ...options,
  });
}

export function useApiMutation<T, V = unknown>(
  endpoint: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE" = "POST",
  options?: Omit<UseMutationOptions<T, ApiError, V>, "mutationFn">,
) {
  return useMutation<T, ApiError, V>({
    mutationFn: (body: V) => {
      if (method === "DELETE") {
        return api.delete<T>(endpoint);
      }
      if (method === "PUT") {
        return api.put<T>(endpoint, body);
      }
      if (method === "PATCH") {
        return api.patch<T>(endpoint, body);
      }
      return api.post<T>(endpoint, body);
    },
    ...options,
  });
}

export function useInvalidateQueries() {
  const queryClient = useQueryClient();

  return (keys: string[]) => {
    return queryClient.invalidateQueries({ queryKey: keys });
  };
}
