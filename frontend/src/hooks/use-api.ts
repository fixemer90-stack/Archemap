"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import { useAuth } from "@/hooks/use-auth";

export function useApiQuery<T>(
  key: string[],
  endpoint: string,
  options?: Omit<UseQueryOptions<T, ApiError>, "queryKey" | "queryFn">,
) {
  const { token } = useAuth();

  return useQuery<T, ApiError>({
    queryKey: key,
    queryFn: () => api.get<T>(endpoint, token || undefined),
    ...options,
  });
}

export function useApiMutation<T, V = unknown>(
  endpoint: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE" = "POST",
  options?: Omit<UseMutationOptions<T, ApiError, V>, "mutationFn">,
) {
  const { token } = useAuth();

  return useMutation<T, ApiError, V>({
    mutationFn: (body: V) => {
      const authToken = token || undefined;
      if (method === "DELETE") {
        return api.delete<T>(endpoint, authToken);
      }
      if (method === "PUT") {
        return api.put<T>(endpoint, body, authToken);
      }
      if (method === "PATCH") {
        return api.patch<T>(endpoint, body, authToken);
      }
      return api.post<T>(endpoint, body, authToken);
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
