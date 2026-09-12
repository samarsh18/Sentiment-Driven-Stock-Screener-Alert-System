import React from 'react';
import { ConfidenceBar } from '../common/ConfidenceBar';
import { EvidenceStrength } from '../../api/types';
import { ShieldCheck, BarChart2, Layers } from 'lucide-react';

interface Props {
  symbol: string;
  confidence?: number;
  evidenceStrength?: EvidenceStrength;
  reason?: string;
  relevanceScore?: number;
}

export const EvidenceCard: React.FC<Props> = ({
  symbol,
  confidence = 0.82,
  evidenceStrength = 'STRONG',
  reason = 'Historical matching across 45 comparable events indicates significant benchmark excess returns over 5D horizon.',
  relevanceScore = 95,
}) => {
  return (
    <div className="bg-surface border border-surface-border p-5 rounded-xl space-y-4">
      <div className="flex items-center justify-between border-b border-surface-border pb-3">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-accent-blue" />
          <h3 className="text-sm font-semibold text-white">Historical Event Evidence & Confidence</h3>
        </div>
        <span className="text-xs font-mono font-bold text-accent-blue bg-accent-blue/10 px-2 py-0.5 rounded border border-accent-blue/20">
          Relevance Score: {relevanceScore}/100
        </span>
      </div>

      <ConfidenceBar confidence={confidence} evidenceStrength={evidenceStrength} />

      <div className="grid grid-cols-3 gap-3 pt-2">
        <div className="bg-background p-3 rounded-lg border border-surface-border text-center">
          <span className="text-[10px] font-mono text-gray-400 block uppercase">1-Day Horizon</span>
          <span className="text-sm font-bold font-mono text-emerald-400">+1.8%</span>
          <span className="text-[10px] text-gray-500 block">74% Pos Rate</span>
        </div>
        <div className="bg-background p-3 rounded-lg border border-surface-border text-center">
          <span className="text-[10px] font-mono text-gray-400 block uppercase">3-Day Horizon</span>
          <span className="text-sm font-bold font-mono text-emerald-400">+3.4%</span>
          <span className="text-[10px] text-gray-500 block">79% Pos Rate</span>
        </div>
        <div className="bg-background p-3 rounded-lg border border-surface-border text-center">
          <span className="text-[10px] font-mono text-gray-400 block uppercase">5-Day Horizon</span>
          <span className="text-sm font-bold font-mono text-emerald-400">+5.2%</span>
          <span className="text-[10px] text-gray-500 block">82% Pos Rate</span>
        </div>
      </div>

      <div className="p-3 bg-surface-hover rounded-lg border border-surface-border text-xs text-gray-300 font-mono leading-relaxed space-y-1">
        <div className="flex items-center space-x-1 text-white font-semibold mb-1">
          <Layers className="w-3.5 h-3.5 text-accent-blue" />
          <span>Wilson 95% Confidence Interval Explanation:</span>
        </div>
        <p>{reason}</p>
      </div>
    </div>
  );
};
