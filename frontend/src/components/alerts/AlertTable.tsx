import React, { useState } from 'react';
import { AlertResponse } from '../../api/types';
import { DecisionBadge } from '../common/DecisionBadge';
import { SeverityBadge } from '../common/SeverityBadge';
import { formatDate } from '../../lib/utils';
import { Link } from 'react-router-dom';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  alerts: AlertResponse[];
}

export const AlertTable: React.FC<Props> = ({ alerts }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="bg-surface border border-surface-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface-hover text-gray-400 uppercase font-mono text-[10px] tracking-wider border-b border-surface-border">
            <tr>
              <th className="py-3 px-4">Time</th>
              <th className="py-3 px-4">Symbol</th>
              <th className="py-3 px-4">Action</th>
              <th className="py-3 px-4">Severity</th>
              <th className="py-3 px-4">Alert ID</th>
              <th className="py-3 px-4 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {alerts.map((alert) => {
              const isExpanded = expandedId === alert.alert_id;
              return (
                <React.Fragment key={alert.alert_id}>
                  <tr
                    onClick={() => toggleExpand(alert.alert_id)}
                    className="hover:bg-surface-hover/50 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4 font-mono text-gray-400 whitespace-nowrap">
                      {formatDate(alert.created_at)}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-white whitespace-nowrap">
                      <Link
                        to={`/stocks/${alert.symbol}`}
                        className="hover:text-accent-blue hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {alert.symbol}
                      </Link>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <DecisionBadge action={alert.action} />
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <SeverityBadge severity={alert.severity} label={alert.severity_label} />
                    </td>
                    <td className="py-3 px-4 font-mono text-gray-400 whitespace-nowrap">
                      {alert.alert_id.slice(0, 16)}...
                    </td>
                    <td className="py-3 px-4 text-right">
                      {isExpanded ? <ChevronUp className="w-4 h-4 ml-auto text-gray-400" /> : <ChevronDown className="w-4 h-4 ml-auto text-gray-400" />}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr className="bg-background/50 border-t-0">
                      <td colSpan={6} className="p-4 space-y-2">
                        <div className="text-xs text-gray-300 font-mono leading-relaxed bg-surface p-3 rounded-lg border border-surface-border">
                          <p className="font-semibold text-white mb-1">Reasoning & Evidence:</p>
                          {alert.message}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
