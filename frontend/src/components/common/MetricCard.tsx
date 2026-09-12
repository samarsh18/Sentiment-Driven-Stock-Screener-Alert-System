import React from 'react';
import { cn } from '../../lib/utils';

interface Props {
  title: string;
  value: React.ReactNode;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  className?: string;
}

export const MetricCard: React.FC<Props> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  className,
}) => {
  return (
    <div className={cn('bg-surface border border-surface-border p-4 rounded-xl shadow-sm hover:border-gray-700 transition-colors', className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">{title}</span>
        {icon && <div className="p-2 bg-surface-hover text-gray-400 rounded-lg">{icon}</div>}
      </div>
      <div className="mt-2 flex items-baseline justify-between">
        <div className="text-2xl font-bold font-mono text-white">{value}</div>
        {trendValue && (
          <span className={cn('text-xs font-mono font-semibold', trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400')}>
            {trendValue}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-gray-400">{subtitle}</p>}
    </div>
  );
};
