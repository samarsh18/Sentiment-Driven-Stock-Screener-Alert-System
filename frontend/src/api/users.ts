/**
 * frontend/src/api/users.ts
 */
import { apiRequest, USE_MOCK } from './client';
import { MOCK_PREFERENCES, MOCK_USER } from './mockData';
import { UserPreferencesResponse, UserPreferencesUpdate, UserResponse } from './types';

export async function createOrGetUser(email: string): Promise<UserResponse> {
  if (USE_MOCK) return { ...MOCK_USER, email };
  return apiRequest<UserResponse>('/users', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export async function getUser(userId: number): Promise<UserResponse> {
  if (USE_MOCK) return MOCK_USER;
  return apiRequest<UserResponse>(`/users/${userId}`);
}

export async function getUserPreferences(userId: number): Promise<UserPreferencesResponse> {
  if (USE_MOCK) return MOCK_PREFERENCES;
  return apiRequest<UserPreferencesResponse>(`/users/${userId}/preferences`);
}

export async function updateUserPreferences(
  userId: number,
  update: UserPreferencesUpdate
): Promise<UserPreferencesResponse> {
  if (USE_MOCK) return { ...MOCK_PREFERENCES, ...update };
  return apiRequest<UserPreferencesResponse>(`/users/${userId}/preferences`, {
    method: 'PUT',
    body: JSON.stringify(update),
  });
}
