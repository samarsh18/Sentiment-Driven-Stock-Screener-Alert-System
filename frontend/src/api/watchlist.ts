/**
 * frontend/src/api/watchlist.ts
 */
import { apiRequest, USE_MOCK } from './client';
import { MOCK_WATCHLIST } from './mockData';
import { WatchlistItemCreate, WatchlistItemResponse, WatchlistResponse } from './types';

export async function getWatchlist(userId: number): Promise<WatchlistResponse> {
  if (USE_MOCK) return MOCK_WATCHLIST;
  return apiRequest<WatchlistResponse>(`/users/${userId}/watchlist`);
}

export async function addWatchlistItem(
  userId: number,
  item: WatchlistItemCreate
): Promise<WatchlistItemResponse> {
  if (USE_MOCK) {
    const newItem: WatchlistItemResponse = {
      id: Date.now(),
      user_id: userId,
      symbol: item.symbol.toUpperCase(),
      company_name: item.company_name,
      created_at: new Date().toISOString(),
    };
    MOCK_WATCHLIST.items.unshift(newItem);
    MOCK_WATCHLIST.total = MOCK_WATCHLIST.items.length;
    return newItem;
  }
  return apiRequest<WatchlistItemResponse>(`/users/${userId}/watchlist`, {
    method: 'POST',
    body: JSON.stringify(item),
  });
}

export async function removeWatchlistItem(userId: number, symbol: string): Promise<void> {
  if (USE_MOCK) {
    MOCK_WATCHLIST.items = MOCK_WATCHLIST.items.filter(
      (i) => i.symbol !== symbol.toUpperCase()
    );
    MOCK_WATCHLIST.total = MOCK_WATCHLIST.items.length;
    return;
  }
  return apiRequest<void>(`/users/${userId}/watchlist/${encodeURIComponent(symbol)}`, {
    method: 'DELETE',
  });
}
