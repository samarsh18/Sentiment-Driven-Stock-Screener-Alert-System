/**
 * frontend/src/api/news.ts
 */
import { apiRequest, USE_MOCK } from './client';
import { MOCK_NEWS } from './mockData';
import { NewsListResponse, NewsRecordResponse } from './types';

export async function getUserNews(
  userId: number,
  limit = 20,
  offset = 0
): Promise<NewsListResponse> {
  if (USE_MOCK) return MOCK_NEWS;
  return apiRequest<NewsListResponse>(`/users/${userId}/news?limit=${limit}&offset=${offset}`);
}

export async function getNewsById(newsId: string): Promise<NewsRecordResponse> {
  if (USE_MOCK) {
    const item = MOCK_NEWS.items.find((n) => n.news_id === newsId) || MOCK_NEWS.items[0];
    return item;
  }
  return apiRequest<NewsRecordResponse>(`/news/${encodeURIComponent(newsId)}`);
}

export async function getStockNews(
  symbol: string,
  limit = 20,
  offset = 0
): Promise<NewsListResponse> {
  if (USE_MOCK) {
    const filtered = MOCK_NEWS.items.filter((n) => n.symbol === symbol.toUpperCase());
    return {
      pagination: { total: filtered.length, limit, offset },
      items: filtered.length ? filtered : MOCK_NEWS.items,
    };
  }
  return apiRequest<NewsListResponse>(
    `/stocks/${encodeURIComponent(symbol)}/news?limit=${limit}&offset=${offset}`
  );
}
