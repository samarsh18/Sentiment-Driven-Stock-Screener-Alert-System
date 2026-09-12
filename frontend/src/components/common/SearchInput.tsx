import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';

export const SearchInput: React.FC = () => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/stocks/${query.trim().toUpperCase()}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-xs">
      <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
      <input
        type="text"
        placeholder="Search ticker (e.g. TCS)..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full bg-surface-hover border border-surface-border text-xs text-white placeholder-gray-500 rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-accent-blue transition-colors font-mono uppercase"
      />
    </form>
  );
};
