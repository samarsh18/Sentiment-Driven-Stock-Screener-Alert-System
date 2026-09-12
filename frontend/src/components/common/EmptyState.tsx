import React from 'react';
import { Inbox } from 'lucide-react';

interface Props {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<Props> = ({
  title = 'No records found',
  description = 'There is no data available for this section yet.',
  action,
}) => {
  return (
    <div className="bg-surface border border-surface-border p-8 rounded-xl flex flex-col items-center justify-center text-center space-y-3">
      <div className="p-3 bg-surface-hover rounded-full text-gray-500">
        <Inbox className="w-6 h-6" />
      </div>
      <h4 className="text-sm font-semibold text-gray-300">{title}</h4>
      <p className="text-xs text-gray-500 max-w-sm">{description}</p>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
};
