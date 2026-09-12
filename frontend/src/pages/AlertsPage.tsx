import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { AlertTable } from '../components/alerts/AlertTable';
import { LoadingCard } from '../components/common/LoadingCard';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { useDemoUser } from '../hooks/useUser';
import { useUserAlerts } from '../hooks/useAlerts';
import { Action, SeverityLabel } from '../api/types';
import { Filter, Bell } from 'lucide-react';

export const AlertsPage: React.FC = () => {
  const { userId } = useDemoUser();
  const { data, isLoading, error, refetch } = useUserAlerts(userId, 50);

  const [filterAction, setFilterAction] = useState<string>('ALL');
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');

  const alerts = data?.items ?? [];

  const filteredAlerts = alerts.filter((alert) => {
    if (filterAction !== 'ALL' && alert.action !== filterAction) return false;
    if (filterSeverity !== 'ALL' && alert.severity_label !== filterSeverity) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Persisted System Alerts"
        subtitle="Historical alert records produced by FinBERT + Gemini + Wilson 95% Confidence decision engine"
      />

      {/* Filter Controls Bar */}
      <div className="bg-surface border border-surface-border p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-accent-blue" />
          <span className="text-xs font-semibold text-white">Filter Alerts</span>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div>
            <label className="text-gray-400 mr-2 font-mono text-[11px]">Action:</label>
            <select
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
              className="bg-surface-hover border border-surface-border text-white rounded-lg px-2.5 py-1.5 font-mono focus:outline-none focus:border-accent-blue"
            >
              <option value="ALL">ALL ACTIONS</option>
              <option value="BUY">BUY</option>
              <option value="OPPORTUNITY">OPPORTUNITY</option>
              <option value="SELL">SELL</option>
              <option value="RISK_ALERT">RISK_ALERT</option>
              <option value="HOLD">HOLD</option>
              <option value="WATCH">WATCH</option>
            </select>
          </div>

          <div>
            <label className="text-gray-400 mr-2 font-mono text-[11px]">Severity:</label>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-surface-hover border border-surface-border text-white rounded-lg px-2.5 py-1.5 font-mono focus:outline-none focus:border-accent-blue"
            >
              <option value="ALL">ALL SEVERITIES</option>
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alerts Table */}
      {isLoading ? (
        <LoadingCard message="Loading alert history..." />
      ) : error ? (
        <ErrorState title="Failed to load alerts" onRetry={refetch} />
      ) : filteredAlerts.length === 0 ? (
        <EmptyState
          title="No alerts match the selected criteria"
          description="Try adjusting your action or severity filter above, or run pipeline analysis to generate alerts."
        />
      ) : (
        <div className="space-y-2">
          <div className="text-xs font-mono text-gray-400 text-right pr-1">
            Showing {filteredAlerts.length} of {alerts.length} total alerts
          </div>
          <AlertTable alerts={filteredAlerts} />
        </div>
      )}
    </div>
  );
};
