import React from 'react';
import { SentimentType } from '../../api/types';
import { cn } from '../../lib/utils';

interface Props {
  sentiment: SentimentType;
  score?: number;
  className?: string;
}

export const SentimentBadge: React.FC<Props> = ({ sentiment, score, className }) => {
  const norm = (sentiment || 'neutral').toLowerCase() as SentimentType;

  const styles: Record<SentimentType, string> = {
    positive: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    negative: 'bg-red-500/10 text-red-400 border-red-500/30',
    neutral: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
  };

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-mono border capitalize', styles[norm] || styles.neutral, className)}>
      {norm}
      {score !== undefined && (
        <span className="ml-1 opacity-75">({score > 0 ? `+${score.toFixed(2)}` : score.toFixed(2)})</span>
      )}
    </span>
  );
};
