/**
 * frontend/src/hooks/useStock.ts
 */
import { useQuery } from '@tanstack/react-query';
import { getStockHistory } from '../api/stocks';

export function useStockHistory(symbol: string, exchange = 'NSE') {
  return useQuery({
    queryKey: ['stockHistory', symbol, exchange],
    queryFn: () => getStockHistory(symbol, exchange),
    enabled: !!symbol,
  });
}
