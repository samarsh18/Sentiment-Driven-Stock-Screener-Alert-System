import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { LoadingCard } from '../components/common/LoadingCard';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { useDemoUser } from '../hooks/useUser';
import { useWatchlist } from '../hooks/useWatchlist';
import { DEFAULT_STOCKS } from '../lib/constants';
import { Bookmark, Plus, Trash2, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

export const WatchlistPage: React.FC = () => {
  const { userId } = useDemoUser();
  const { items, isLoading, error, refetch, addStock, isAdding, removeStock } = useWatchlist(userId);

  const [newSymbol, setNewSymbol] = useState('');
  const [newCompanyName, setNewCompanyName] = useState('');

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (newSymbol.trim()) {
      addStock(
        {
          symbol: newSymbol.trim().toUpperCase(),
          company_name: newCompanyName.trim() || `${newSymbol.trim().toUpperCase()} Inc`,
        },
        {
          onSuccess: () => {
            setNewSymbol('');
            setNewCompanyName('');
          },
        }
      );
    }
  };

  const handleAddDefault = (sym: string, name: string) => {
    addStock({ symbol: sym, company_name: name });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monitored Watchlist"
        subtitle="Manage stock symbols monitored by the news ingestion pipeline & historical confidence engine"
      />

      {/* Add Stock Form Card */}
      <div className="bg-surface border border-surface-border p-4 rounded-xl space-y-3">
        <h3 className="text-sm font-semibold text-white flex items-center">
          <Plus className="w-4 h-4 mr-1.5 text-accent-blue" />
          Add Symbol to Watchlist
        </h3>

        <form onSubmit={handleAdd} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="Ticker Symbol (e.g. TCS)"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            className="bg-surface-hover border border-surface-border text-xs text-white placeholder-gray-500 rounded-lg px-3 py-2 font-mono uppercase focus:outline-none focus:border-accent-blue w-full sm:w-48"
            required
          />
          <input
            type="text"
            placeholder="Company Name (optional)"
            value={newCompanyName}
            onChange={(e) => setNewCompanyName(e.target.value)}
            className="bg-surface-hover border border-surface-border text-xs text-white placeholder-gray-500 rounded-lg px-3 py-2 focus:outline-none focus:border-accent-blue flex-1"
          />
          <button
            type="submit"
            disabled={isAdding}
            className="px-4 py-2 bg-accent-blue text-slate-950 text-xs font-bold rounded-lg hover:bg-blue-400 transition-colors disabled:opacity-50 flex items-center justify-center shrink-0"
          >
            {isAdding ? 'Adding...' : 'Add Stock'}
          </button>
        </form>

        {/* Quick Add Presets */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-surface-border text-xs">
          <span className="text-gray-400 text-[11px]">Quick Add Presets:</span>
          {DEFAULT_STOCKS.map((stk) => {
            const alreadyIn = items.some((i) => i.symbol === stk.symbol);
            return (
              <button
                key={stk.symbol}
                onClick={() => !alreadyIn && handleAddDefault(stk.symbol, stk.company_name)}
                disabled={alreadyIn}
                className={`px-2 py-1 rounded text-[11px] font-mono border transition-colors ${
                  alreadyIn
                    ? 'bg-surface-hover text-gray-500 border-surface-border cursor-not-allowed'
                    : 'bg-accent-blue/10 text-accent-blue border-accent-blue/20 hover:bg-accent-blue/20'
                }`}
              >
                + {stk.symbol}
              </button>
            );
          })}
        </div>
      </div>

      {/* Watchlist Table / Grid */}
      {isLoading ? (
        <LoadingCard message="Loading watchlist stocks..." />
      ) : error ? (
        <ErrorState title="Failed to load watchlist" onRetry={refetch} />
      ) : items.length === 0 ? (
        <EmptyState
          title="Your watchlist is empty"
          description="Add symbols above or click one of the quick presets to start monitoring stocks."
        />
      ) : (
        <div className="bg-surface border border-surface-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-hover text-gray-400 uppercase font-mono text-[10px] tracking-wider border-b border-surface-border">
                <tr>
                  <th className="py-3 px-4">Symbol</th>
                  <th className="py-3 px-4">Company Name</th>
                  <th className="py-3 px-4">Added On</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-hover/50 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-white text-sm">
                      <Link to={`/stocks/${item.symbol}`} className="hover:text-accent-blue hover:underline">
                        {item.symbol}
                      </Link>
                    </td>
                    <td className="py-3.5 px-4 text-gray-300 font-medium">{item.company_name}</td>
                    <td className="py-3.5 px-4 font-mono text-gray-400">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <Link
                        to={`/stocks/${item.symbol}`}
                        className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold bg-accent-blue/10 text-accent-blue border border-accent-blue/20 hover:bg-accent-blue/20 transition-colors"
                      >
                        Analyze
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                      <button
                        onClick={() => removeStock(item.symbol)}
                        className="inline-flex items-center p-1 rounded text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        title="Remove stock"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
