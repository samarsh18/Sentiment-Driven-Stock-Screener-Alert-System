import React from 'react';
import { Action } from '../../api/types';
import { cn } from '../../lib/utils';
import { TrendingUp, TrendingDown, Eye, AlertTriangle, CheckCircle, Info } from 'lucide-react';

interface Props {
  action: Action;
  className?: string;
}

export const DecisionBadge: React.FC<Props> = ({ action, className }) => {
  const normalized = action?.toUpperCase() as Action;

  const styles: Record<string, { bg: string; text: string; border: string; icon: React.ReactNode }> = {
    BUY: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30', icon: <TrendingUp className="w-3.5 h-3.5 mr-1" /> },
    OPPORTUNITY: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30', icon: <CheckCircle className="w-3.5 h-3.5 mr-1" /> },
    SELL: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', icon: <TrendingDown className="w-3.5 h-3.5 mr-1" /> },
    RISK_ALERT: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', icon: <AlertTriangle className="w-3.5 h-3.5 mr-1" /> },
    HOLD: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30', icon: <Info className="w-3.5 h-3.5 mr-1" /> },
    WATCH: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', icon: <Eye className="w-3.5 h-3.5 mr-1" /> },
    INFORMATIONAL: { bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500/30', icon: <Info className="w-3.5 h-3.5 mr-1" /> },
  };

  const style = styles[normalized] || styles.INFORMATIONAL;

  return (
    <span className={cn('inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border', style.bg, style.text, style.border, className)}>
      {style.icon}
      {normalized}
    </span>
  );
};
