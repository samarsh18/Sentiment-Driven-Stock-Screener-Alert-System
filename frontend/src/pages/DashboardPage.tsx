import React from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { MetricCard } from '../components/common/MetricCard';
import { MarketStatusHeader } from '../components/dashboard/MarketStatusHeader';
import { QuickAnalysisWidget } from '../components/dashboard/QuickAnalysisWidget';
import { NewsCard } from '../components/news/NewsCard';
import { AlertTable } from '../components/alerts/AlertTable';
import { LoadingCard } from '../components/common/LoadingCard';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { useDemoUser } from '../hooks/useUser';
import { useWatchlist } from '../hooks/useWatchlist';
import { useUserNews } from '../hooks/useNews';
import { useUserAlerts } from '../hooks/useAlerts';
import { Bookmark, Bell, Newspaper, TrendingUp, ShieldAlert, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const { userId } = useDemoUser();
  const { items: watchlistItems, isLoading: wlLoading, refetch: refetchWatchlist } = useWatchlist(userId);
  const { data: newsData, isLoading: newsLoading, isError: newsError, refetch: refetchNews } = useUserNews(userId, 6);
  const { data: alertsData, isLoading: alertsLoading, isError: alertsError, refetch: refetchAlerts } = useUserAlerts(userId, 10);

  const handleRefreshAll = () => {
    refetchWatchlist();
    refetchNews();
    refetchAlerts();
  };

  const buyAlertsCount = alertsData?.items.filter((a) => a.action === 'BUY' || a.action === 'OPPORTUNITY').length ?? 0;
  const riskAlertsCount = alertsData?.items.filter((a) => a.action === 'SELL' || a.action === 'RISK_ALERT').length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Intelligence Dashboard"
        subtitle="Real-time financial sentiment, historical event study & evidence-based signal screener"
      />

      <MarketStatusHeader onRefresh={handleRefreshAll} />

      {/* Top Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Watchlist Stocks"
          value={wlLoading ? '...' : watchlistItems.length}
          subtitle="Actively monitored tickers"
          icon={<Bookmark className="w-4 h-4 text-accent-blue" />}
        />
        <MetricCard
          title="Generated Alerts"
          value={alertsLoading ? '...' : alertsData?.pagination.total ?? 0}
          subtitle="System alerts stored"
          icon={<Bell className="w-4 h-4 text-amber-400" />}
        />
        <MetricCard
          title="Opportunity Signals"
          value={buyAlertsCount}
          subtitle="BUY / OPPORTUNITY signals"
          icon={<TrendingUp className="w-4 h-4 text-emerald-400" />}
          trend="up"
        />
        <MetricCard
          title="Risk Alerts"
          value={riskAlertsCount}
          subtitle="SELL / RISK_ALERT signals"
          icon={<ShieldAlert className="w-4 h-4 text-red-400" />}
          trend="down"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Quick Pipeline Analysis + Watchlist Quick Access */}
        <div className="lg:col-span-1 space-y-6">
          <QuickAnalysisWidget userId={userId} />

          {/* Watchlist Summary Card */}
          <div className="bg-surface border border-surface-border p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Monitored Watchlist</h3>
              <Link to="/watchlist" className="text-xs font-semibold text-accent-blue hover:underline">
                View All ({watchlistItems.length})
              </Link>
            </div>

            {wlLoading ? (
              <LoadingCard message="Loading watchlist..." />
            ) : watchlistItems.length === 0 ? (
              <EmptyState title="No stocks monitored" description="Add tickers to start monitoring news." />
            ) : (
              <div className="space-y-2">
                {watchlistItems.slice(0, 5).map((item) => (
                  <Link
                    key={item.id}
                    to={`/stocks/${item.symbol}`}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-surface-hover hover:border-gray-600 border border-surface-border transition-colors group"
                  >
                    <div>
                      <span className="font-mono text-xs font-bold text-white group-hover:text-accent-blue transition-colors">
                        {item.symbol}
                      </span>
                      <p className="text-[11px] text-gray-400 line-clamp-1">{item.company_name}</p>
                    </div>
                    <span className="text-[10px] font-mono text-gray-500">Analyze →</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Recent Alerts & Relevant News */}
        <div className="lg:col-span-2 space-y-6">
          {/* Latest Alerts Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Bell className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-white">Latest High-Confidence Alerts</h3>
              </div>
              <Link to="/alerts" className="text-xs font-semibold text-accent-blue hover:underline">
                View All Alerts →
              </Link>
            </div>

            {alertsLoading ? (
              <LoadingCard message="Loading recent alerts..." />
            ) : alertsError ? (
              <ErrorState title="Failed to load alerts" onRetry={refetchAlerts} />
            ) : !alertsData || alertsData.items.length === 0 ? (
              <EmptyState
                title="No alerts generated yet"
                description="Run the quick pipeline widget on the left to analyze news and generate an alert."
              />
            ) : (
              <AlertTable alerts={alertsData.items.slice(0, 5)} />
            )}
          </div>

          {/* Recent Relevant News Feed */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Newspaper className="w-4 h-4 text-accent-blue" />
                <h3 className="text-sm font-semibold text-white">Recent Relevant News</h3>
              </div>
            </div>

            {newsLoading ? (
              <LoadingCard message="Fetching ingested news feed..." />
            ) : newsError ? (
              <ErrorState title="Failed to load news" onRetry={refetchNews} />
            ) : !newsData || newsData.items.length === 0 ? (
              <EmptyState title="No news ingested yet" description="New articles will appear as news providers ingest data." />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {newsData.items.map((news) => (
                  <NewsCard key={news.id} news={news} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
