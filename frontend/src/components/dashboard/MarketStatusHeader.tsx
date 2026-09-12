import React from 'react';
import { RefreshCw, Radio } from 'lucide-react';

interface Props {
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const MarketStatusHeader: React.FC<Props> = ({ onRefresh, isRefreshing }) => {
  return (
    <div className="bg-surface border border-surface-border p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
          <Radio className="w-4 h-4 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-semibold text-white">Monitoring Service</h3>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              LIVE
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            GDELT News Feed • FinBERT Sentiment • Gemini 2.5 • Wilson 95% CI Matcher
          </p>
        </div>
      </div>

      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-hover text-gray-200 border border-surface-border hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh Pipeline
        </button>
      )}
    </div>
  );
};
