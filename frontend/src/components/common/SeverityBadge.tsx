import React from 'react';
import { SeverityLabel } from '../../api/types';
import { cn } from '../../lib/utils';

interface Props {
  severity: number | SeverityLabel;
  label?: SeverityLabel;
  className?: string;
}

export const SeverityBadge: React.FC<Props> = ({ severity, label, className }) => {
  let displayLabel: string = label || 'LOW';
  if (typeof severity === 'string') {
    displayLabel = severity;
  } else if (typeof severity === 'number') {
    if (severity >= 7) displayLabel = 'HIGH';
    else if (severity >= 4) displayLabel = 'MEDIUM';
    else displayLabel = 'LOW';
  }

  const styles: Record<string, string> = {
    LOW: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    MEDIUM: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    HIGH: 'bg-red-500/10 text-red-400 border-red-500/30',
    CRITICAL: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  };

  const badgeStyle = styles[displayLabel.toUpperCase()] || styles.LOW;

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium border', badgeStyle, className)}>
      SEV-{displayLabel.toUpperCase()}
    </span>
  );
};
