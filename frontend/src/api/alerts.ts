/**
 * frontend/src/api/alerts.ts
 */
import { apiRequest, USE_MOCK } from './client';
import { MOCK_ALERTS } from './mockData';
import { AlertListResponse, AlertResponse } from './types';

export async function getUserAlerts(
  userId: number,
  limit = 20,
  offset = 0
): Promise<AlertListResponse> {
  if (USE_MOCK) return MOCK_ALERTS;
  return apiRequest<AlertListResponse>(`/users/${userId}/alerts?limit=${limit}&offset=${offset}`);
}

export async function getUserAlertById(userId: number, alertId: string): Promise<AlertResponse> {
  if (USE_MOCK) {
    const item = MOCK_ALERTS.items.find((a) => a.alert_id === alertId) || MOCK_ALERTS.items[0];
    return item;
  }
  return apiRequest<AlertResponse>(
    `/users/${userId}/alerts/${encodeURIComponent(alertId)}`
  );
}
