/**
 * frontend/src/hooks/useAlerts.ts
 */
import { useQuery } from '@tanstack/react-query';
import { getUserAlertById, getUserAlerts } from '../api/alerts';

export function useUserAlerts(userId: number, limit = 20) {
  return useQuery({
    queryKey: ['userAlerts', userId, limit],
    queryFn: () => getUserAlerts(userId, limit),
    enabled: !!userId,
    refetchInterval: 30000,
  });
}

export function useAlertById(userId: number, alertId: string) {
  return useQuery({
    queryKey: ['alertById', userId, alertId],
    queryFn: () => getUserAlertById(userId, alertId),
    enabled: !!userId && !!alertId,
  });
}
