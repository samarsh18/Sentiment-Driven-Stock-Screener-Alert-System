import React from 'react';
import { EvidenceStrength } from '../../api/types';
import { cn, formatPercent } from '../../lib/utils';

interface Props {
  confidence: number;
  evidenceStrength?: EvidenceStrength;
  showBar?: boolean;
  className?: string;
}

export const ConfidenceBar: React.FC<Props> = ({
  confidence,
  evidenceStrength = 'MODERATE',
  showBar = true,
  className,
}) => {
  const percentage = Math.min(100, Math.max(0, confidence * 100));

  const strengthStyles: Record<EvidenceStrength, { text: string; bg: string }> = {
    STRONG: { text: 'text-emerald-400', bg: 'bg-emerald-500' },
    MODERATE: { text: 'text-blue-400', bg: 'bg-blue-500' },
    WEAK: { text: 'text-amber-400', bg: 'bg-amber-500' },
    INSUFFICIENT: { text: 'text-gray-400', bg: 'bg-gray-500' },
  };

  const style = strengthStyles[evidenceStrength] || strengthStyles.MODERATE;

  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono text-gray-300 font-medium">
          Confidence: <span className="text-white font-bold">{formatPercent(confidence)}</span>
        </span>
        {evidenceStrength && (
          <span className={cn('font-mono text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-surface-hover', style.text)}>
            {evidenceStrength} EVIDENCE
          </span>
        )}
      </div>

      {showBar && (
        <div className="h-1.5 w-full bg-surface-hover rounded-full overflow-hidden">
          <div
            className={cn('h-full transition-all duration-500 rounded-full', style.bg)}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}
    </div>
  );
};
