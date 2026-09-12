import React, { useState } from 'react';
import { usePipelineAnalyze } from '../../hooks/usePipeline';
import { DecisionBadge } from '../common/DecisionBadge';
import { ConfidenceBar } from '../common/ConfidenceBar';
import { SeverityBadge } from '../common/SeverityBadge';
import { SentimentBadge } from '../common/SentimentBadge';
import { Sparkles, Play, AlertCircle } from 'lucide-react';

interface Props {
  userId: number;
}

export const QuickAnalysisWidget: React.FC<Props> = ({ userId }) => {
  const [symbol, setSymbol] = useState('TCS');
  const [companyName, setCompanyName] = useState('Tata Consultancy Services');
  const [title, setTitle] = useState('TCS reports strong Q4 earnings beat (+14% YoY)');
  const [content, setContent] = useState(
    'Tata Consultancy Services reported strong quarterly earnings surpassing analyst estimates driven by digital transformation deal wins.'
  );

  const { mutate: analyze, data: result, isPending, error } = usePipelineAnalyze();

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    analyze({
      news_item: {
        news_id: `DEMO-${Date.now()}`,
        symbol: symbol.toUpperCase(),
        company_name: companyName,
        title,
        content,
        source: 'Live Demo Input',
        url: 'https://example.com/news',
        published_at: new Date().toISOString(),
      },
      stock_metadata: {
        symbol: symbol.toUpperCase(),
        company_name: companyName,
        exchange: 'NSE',
      },
      persist_alert: true,
      user_id: userId,
    });
  };

  return (
    <div className="bg-surface border border-surface-border p-5 rounded-xl space-y-4">
      <div className="flex items-center space-x-2">
        <Sparkles className="w-5 h-5 text-accent-blue" />
        <h3 className="text-sm font-semibold text-white">Live Pipeline Trigger (POST /api/pipeline/analyze)</h3>
      </div>

      <form onSubmit={handleAnalyze} className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-[11px] font-mono text-gray-400 mb-1">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-full bg-surface-hover border border-surface-border text-xs text-white rounded-lg px-3 py-2 font-mono uppercase focus:outline-none focus:border-accent-blue"
              required
            />
          </div>
          <div>
            <label className="block text-[11px] font-mono text-gray-400 mb-1">Company Name</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="w-full bg-surface-hover border border-surface-border text-xs text-white rounded-lg px-3 py-2 focus:outline-none focus:border-accent-blue"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-[11px] font-mono text-gray-400 mb-1">Article Headline</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-surface-hover border border-surface-border text-xs text-white rounded-lg px-3 py-2 focus:outline-none focus:border-accent-blue"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isPending}
          className="w-full inline-flex items-center justify-center px-4 py-2 rounded-lg text-xs font-bold bg-accent-blue text-slate-950 hover:bg-blue-400 transition-colors disabled:opacity-50"
        >
          {isPending ? (
            <span className="flex items-center">
              <span className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin mr-2" />
              Running FinBERT + Gemini + Wilson CI...
            </span>
          ) : (
            <span className="flex items-center">
              <Play className="w-3.5 h-3.5 mr-1.5 fill-slate-950" />
              Run Pipeline Analysis & Persist Alert
            </span>
          )}
        </button>
      </form>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center space-x-2 text-xs text-red-400">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{(error as Error).message}</span>
        </div>
      )}

      {result && (
        <div className="mt-4 p-4 bg-surface-hover border border-accent-blue/30 rounded-xl space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border pb-3">
            <div className="flex items-center space-x-2">
              <span className="font-mono font-bold text-white text-base">{result.symbol}</span>
              <DecisionBadge action={result.action} />
              <SeverityBadge severity={result.severity_label} />
              <SentimentBadge sentiment={result.sentiment} score={result.sentiment_score} />
            </div>
            {result.alert_id && (
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                Alert Saved: {result.alert_id.slice(0, 12)}...
              </span>
            )}
          </div>

          <ConfidenceBar confidence={result.confidence} evidenceStrength={result.evidence_strength} />

          <p className="text-xs text-gray-300 bg-background p-3 rounded-lg border border-surface-border leading-relaxed font-mono">
            {result.reason}
          </p>
        </div>
      )}
    </div>
  );
};
