import React from 'react';

export const LoadingCard: React.FC<{ message?: string }> = ({ message = 'Loading market intelligence...' }) => {
  return (
    <div className="bg-surface border border-surface-border p-8 rounded-xl flex flex-col items-center justify-center text-center space-y-3">
      <div className="w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      <p className="text-sm font-medium text-gray-400 font-mono">{message}</p>
    </div>
  );
};
