/**
 * frontend/src/api/stocks.ts
 */
import { apiRequest, USE_MOCK } from './client';
import { MOCK_PRICES } from './mockData';
import { PricesListResponse } from './types';

export async function getStockHistory(
  symbol: string,
  exchange = 'NSE',
  start?: string,
  end?: string
): Promise<PricesListResponse> {
  if (USE_MOCK) {
    const cleanSym = symbol.toUpperCase();
    return (
      MOCK_PRICES[cleanSym] || {
        symbol: cleanSym,
        exchange,
        total: 5,
        items: [
          { symbol: cleanSym, exchange, timestamp: '2024-05-01', open: 100, high: 105, low: 99, close: 102, volume: 50000 },
          { symbol: cleanSym, exchange, timestamp: '2024-05-02', open: 102, high: 108, low: 101, close: 106, volume: 60000 },
          { symbol: cleanSym, exchange, timestamp: '2024-05-03', open: 106, high: 110, low: 104, close: 108, volume: 55000 },
          { symbol: cleanSym, exchange, timestamp: '2024-05-06', open: 108, high: 112, low: 107, close: 111, volume: 70000 },
          { symbol: cleanSym, exchange, timestamp: '2024-05-07', open: 111, high: 115, low: 110, close: 114, volume: 80000 },
        ],
      }
    );
  }

  let query = `/stocks/${encodeURIComponent(symbol)}/history?exchange=${exchange}`;
  if (start) query += `&start=${encodeURIComponent(start)}`;
  if (end) query += `&end=${encodeURIComponent(end)}`;

  return apiRequest<PricesListResponse>(query);
}
