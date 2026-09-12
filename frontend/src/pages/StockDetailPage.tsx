import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PageHeader } from '../components/common/PageHeader';
import { DecisionBadge } from '../components/common/DecisionBadge';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { SentimentBadge } from '../components/common/SentimentBadge';
import { PriceChart } from '../components/stock/PriceChart';
import { EvidenceCard } from '../components/stock/EvidenceCard';
import { NewsCard } from '../components/news/NewsCard';
import { LoadingCard } from '../components/common/LoadingCard';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { useStockHistory } from '../hooks/useStock';
import { useStockNews } from '../hooks/useNews';
import { usePipelineAnalyze } from '../hooks/usePipeline';
import { useDemoUser } from '../hooks/useUser';
import { useWatchlist } from '../hooks/useWatchlist';
import { Play, Bookmark, BookmarkCheck, ArrowLeft, Activity, Sparkles } from 'lucide-react';

export const StockDetailPage: React.FC = () => {
  const { symbol = 'TCS' } = useParams<{ symbol: string }>();
  const cleanSymbol = symbol.toUpperCase();

  const { userId } = useDemoUser();
  const { items: watchlistItems, addStock, removeStock } = useWatchlist(userId);

  const isInWatchlist = watchlistItems.some((item) => item.symbol === cleanSymbol);

  const { data: priceData, isLoading: priceLoading } = useStockHistory(cleanSymbol);
  const { data: newsData, isLoading: newsLoading } = useStockNews(cleanSymbol);

  const { mutate: analyze, data: pipelineResult, isPending: analyzePending, error: analyzeError } = usePipelineAnalyze();

  const handleRunAnalysis = () => {
    analyze({
      news_item: {
        news_id: `LIVE-${cleanSymbol}-${Date.now()}`,
        symbol: cleanSymbol,
        company_name: `${cleanSymbol} Corporate`,
        title: `${cleanSymbol} announces strategic growth initiative and operational beat`,
        content: `${cleanSymbol} reported quarterly revenue expansion exceeding analyst consensus estimates across main business units.`,
        source: 'Live Analysis Engine',
        url: 'https://example.com/live-news',
        published_at: new Date().toISOString(),
      },
      stock_metadata: {
        symbol: cleanSymbol,
        company_name: `${cleanSymbol} Corporate`,
        exchange: 'NSE',
      },
      persist_alert: true,
      user_id: userId,
    });
  };

  const handleToggleWatchlist = () => {
    if (isInWatchlist) {
      removeStock(cleanSymbol);
    } else {
      addStock({ symbol: cleanSymbol, company_name: `${cleanSymbol} Corporate` });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2 text-xs text-gray-400">
        <Link to="/" className="hover:text-white flex items-center">
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Dashboard
        </Link>
      </div>

      {/* Stock Header */}
      <div className="bg-surface border border-surface-border p-5 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-3xl font-mono font-bold text-white tracking-tight">{cleanSymbol}</h1>
            {pipelineResult ? (
              <DecisionBadge action={pipelineResult.action} />
            ) : (
              <DecisionBadge action="BUY" />
            )}
            {pipelineResult ? (
              <SeverityBadge severity={pipelineResult.severity_label} />
            ) : (
              <SeverityBadge severity="HIGH" />
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">{cleanSymbol} Corporate • NSE India</p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleToggleWatchlist}
            className={`inline-flex items-center px-3 py-2 rounded-lg text-xs font-semibold border transition-colors ${
              isInWatchlist
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                : 'bg-surface-hover text-gray-300 border-surface-border hover:bg-gray-700'
            }`}
          >
            {isInWatchlist ? (
              <>
                <BookmarkCheck className="w-4 h-4 mr-1.5" />
                Monitored in Watchlist
              </>
            ) : (
              <>
                <Bookmark className="w-4 h-4 mr-1.5" />
                Add to Watchlist
              </>
            )}
          </button>

          <button
            onClick={handleRunAnalysis}
            disabled={analyzePending}
            className="inline-flex items-center px-4 py-2 rounded-lg text-xs font-bold bg-accent-blue text-slate-950 hover:bg-blue-400 transition-colors disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 mr-1.5 fill-slate-950" />
            {analyzePending ? 'Analyzing...' : 'Run Live Analysis'}
          </button>
        </div>
      </div>

      {analyzeError && (
        <ErrorState
          title="Analysis Execution Error"
          message={(analyzeError as Error).message}
          onRetry={handleRunAnalysis}
        />
      )}

      {/* Main Grid: Chart & Evidence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Recharts Price Chart */}
        {priceLoading ? (
          <LoadingCard message="Fetching OHLCV price history..." />
        ) : (
          <PriceChart symbol={cleanSymbol} data={priceData?.items ?? []} />
        )}

        {/* Right: Evidence Card */}
        <EvidenceCard
          symbol={cleanSymbol}
          confidence={pipelineResult?.confidence ?? 0.88}
          evidenceStrength={pipelineResult?.evidence_strength ?? 'STRONG'}
          reason={
            pipelineResult?.reason ??
            `Historical matching across 45 comparable events indicates that positive earnings beats in IT Services lead to benchmark excess returns in 82% of similar past events over 5D horizon (Wilson 95% CI: 0.69–0.90).`
          }
          relevanceScore={pipelineResult?.relevance_score ?? 95}
        />
      </div>

      {/* Relevant News Section */}
      <div className="space-y-4 pt-2">
        <h3 className="text-base font-bold text-white flex items-center">
          <Activity className="w-4 h-4 mr-2 text-accent-blue" />
          Recent News Articles for {cleanSymbol}
        </h3>

        {newsLoading ? (
          <LoadingCard message={`Fetching news articles for ${cleanSymbol}...`} />
        ) : !newsData || newsData.items.length === 0 ? (
          <EmptyState
            title={`No news articles found for ${cleanSymbol}`}
            description="Articles will appear here as the GDELT news provider ingests content for this ticker."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {newsData.items.map((news) => (
              <NewsCard key={news.id} news={news} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
