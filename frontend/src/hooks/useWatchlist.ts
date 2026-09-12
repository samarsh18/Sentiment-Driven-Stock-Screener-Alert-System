/**
 * frontend/src/hooks/useWatchlist.ts
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { addWatchlistItem, getWatchlist, removeWatchlistItem } from '../api/watchlist';

export function useWatchlist(userId: number) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['watchlist', userId],
    queryFn: () => getWatchlist(userId),
    enabled: !!userId,
    refetchInterval: 30000, // conservative auto-refresh
  });

  const addMutation = useMutation({
    mutationFn: ({ symbol, company_name }: { symbol: string; company_name: string }) =>
      addWatchlistItem(userId, { symbol, company_name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist', userId] });
      queryClient.invalidateQueries({ queryKey: ['userNews', userId] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (symbol: string) => removeWatchlistItem(userId, symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist', userId] });
      queryClient.invalidateQueries({ queryKey: ['userNews', userId] });
    },
  });

  return {
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    addStock: addMutation.mutate,
    isAdding: addMutation.isPending,
    removeStock: removeMutation.mutate,
    isRemoving: removeMutation.isPending,
  };
}
