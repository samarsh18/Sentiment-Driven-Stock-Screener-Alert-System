/**
 * frontend/src/hooks/useNews.ts
 */
import { useQuery } from '@tanstack/react-query';
import { getNewsById, getStockNews, getUserNews } from '../api/news';

export function useUserNews(userId: number, limit = 20) {
  return useQuery({
    queryKey: ['userNews', userId, limit],
    queryFn: () => getUserNews(userId, limit),
    enabled: !!userId,
    refetchInterval: 60000,
  });
}

export function useStockNews(symbol: string, limit = 20) {
  return useQuery({
    queryKey: ['stockNews', symbol, limit],
    queryFn: () => getStockNews(symbol, limit),
    enabled: !!symbol,
  });
}

export function useNewsById(newsId: string) {
  return useQuery({
    queryKey: ['newsById', newsId],
    queryFn: () => getNewsById(newsId),
    enabled: !!newsId,
  });
}
