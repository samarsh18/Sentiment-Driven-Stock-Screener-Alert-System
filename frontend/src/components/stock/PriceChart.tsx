import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { PriceBarResponse } from '../../api/types';
import { formatDate } from '../../lib/utils';

interface Props {
  symbol: string;
  data: PriceBarResponse[];
}

export const PriceChart: React.FC<Props> = ({ symbol, data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 bg-surface border border-surface-border rounded-xl flex items-center justify-center text-xs text-gray-500 font-mono">
        No price history bars recorded for {symbol}
      </div>
    );
  }

  const chartData = data.map((bar) => ({
    time: formatDate(bar.timestamp),
    close: bar.close,
    open: bar.open,
    high: bar.high,
    low: bar.low,
    volume: bar.volume,
  }));

  const isUp = chartData.length > 1 && chartData[chartData.length - 1].close >= chartData[0].close;
  const strokeColor = isUp ? '#3fb950' : '#f85149';
  const fillColor = isUp ? 'rgba(63, 185, 80, 0.15)' : 'rgba(248, 81, 73, 0.15)';

  return (
    <div className="bg-surface border border-surface-border p-4 rounded-xl space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white">Historical OHLCV Price Chart</h3>
          <p className="text-xs text-gray-400 font-mono">{symbol} • {data.length} Daily Bars</p>
        </div>
        <div className="text-right font-mono">
          <span className="text-lg font-bold text-white">${chartData[chartData.length - 1].close.toFixed(2)}</span>
        </div>
      </div>

      <div className="h-64 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={strokeColor} stopOpacity={0.4} />
                <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
            <XAxis dataKey="time" stroke="#6e7681" fontSize={10} tickLine={false} />
            <YAxis stroke="#6e7681" fontSize={10} domain={['auto', 'auto']} tickLine={false} orientation="right" />
            <Tooltip
              contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d', borderRadius: '8px', fontSize: '12px', color: '#fff' }}
              itemStyle={{ color: strokeColor }}
            />
            <Area type="monotone" dataKey="close" stroke={strokeColor} strokeWidth={2} fillOpacity={1} fill="url(#priceGradient)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
