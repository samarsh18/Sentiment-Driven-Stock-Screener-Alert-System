/**
 * frontend/src/hooks/useUser.ts
 * Demo User Provisioning & User Preferences Hook.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createOrGetUser, getUserPreferences, updateUserPreferences } from '../api/users';
import { DEMO_EMAIL, STORAGE_USER_KEY } from '../lib/constants';

export function useDemoUser() {
  const query = useQuery({
    queryKey: ['demoUser'],
    queryFn: async () => {
      // Check stored ID first
      const storedIdStr = localStorage.getItem(STORAGE_USER_KEY);
      if (storedIdStr) {
        const storedId = parseInt(storedIdStr, 10);
        if (!isNaN(storedId)) {
          return { id: storedId, email: DEMO_EMAIL, is_active: true, created_at: new Date().toISOString() };
        }
      }
      // Provision via POST /api/users
      const user = await createOrGetUser(DEMO_EMAIL);
      localStorage.setItem(STORAGE_USER_KEY, user.id.toString());
      return user;
    },
    staleTime: Infinity,
  });

  return {
    userId: query.data?.id ?? 1,
    user: query.data,
    isLoading: query.isLoading,
    error: query.error,
  };
}

export function useUserPreferences(userId: number) {
  const queryClient = useQueryClient();

  const preferencesQuery = useQuery({
    queryKey: ['userPreferences', userId],
    queryFn: () => getUserPreferences(userId),
    enabled: !!userId,
  });

  const updateMutation = useMutation({
    mutationFn: (active: boolean) => updateUserPreferences(userId, { is_active: active }),
    onSuccess: (data) => {
      queryClient.setQueryData(['userPreferences', userId], data);
    },
  });

  return {
    preferences: preferencesQuery.data,
    isLoading: preferencesQuery.isLoading,
    error: preferencesQuery.error,
    updatePreferences: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
  };
}
