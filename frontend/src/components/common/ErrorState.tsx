import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<Props> = ({
  title = 'API Request Error',
  message = 'Backend API unavailable. Make sure FastAPI server is running on http://localhost:8000',
  onRetry,
}) => {
  return (
    <div className="bg-surface border border-red-500/30 p-6 rounded-xl flex flex-col items-center justify-center text-center space-y-3">
      <div className="p-3 bg-red-500/10 rounded-full text-red-400">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h4 className="text-base font-semibold text-white">{title}</h4>
      <p className="text-xs text-gray-400 max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-hover text-gray-200 border border-surface-border hover:bg-gray-700 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
          Retry Request
        </button>
      )}
    </div>
  );
};
