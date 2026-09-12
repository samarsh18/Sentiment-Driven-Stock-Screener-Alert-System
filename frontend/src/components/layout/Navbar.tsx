import React from 'react';
import { NavLink } from 'react-router-dom';
import { SearchInput } from '../common/SearchInput';
import { Activity, LayoutDashboard, Bookmark, Bell, Settings } from 'lucide-react';
import { USE_MOCK } from '../../api/client';

interface Props {
  userId: number;
}

export const Navbar: React.FC<Props> = ({ userId }) => {
  return (
    <header className="bg-surface border-b border-surface-border px-4 py-3 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-4">
        <div className="md:hidden flex items-center space-x-2">
          <Activity className="w-5 h-5 text-accent-blue" />
          <span className="font-bold text-sm text-white">Screener AI</span>
        </div>
        <SearchInput />
      </div>

      <div className="flex items-center space-x-3 text-xs">
        <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-surface-hover border border-surface-border text-gray-400">
          User #{userId}
        </span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono border ${USE_MOCK ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'}`}>
          <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${USE_MOCK ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'}`} />
          {USE_MOCK ? 'MOCK MODE' : 'REAL API (PORT 8000)'}
        </span>
      </div>

      {/* Mobile nav links */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-surface border-t border-surface-border p-2 flex justify-around z-40">
        <NavLink to="/" end className={({ isActive }) => `p-2 ${isActive ? 'text-accent-blue' : 'text-gray-400'}`}>
          <LayoutDashboard className="w-5 h-5" />
        </NavLink>
        <NavLink to="/watchlist" className={({ isActive }) => `p-2 ${isActive ? 'text-accent-blue' : 'text-gray-400'}`}>
          <Bookmark className="w-5 h-5" />
        </NavLink>
        <NavLink to="/alerts" className={({ isActive }) => `p-2 ${isActive ? 'text-accent-blue' : 'text-gray-400'}`}>
          <Bell className="w-5 h-5" />
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `p-2 ${isActive ? 'text-accent-blue' : 'text-gray-400'}`}>
          <Settings className="w-5 h-5" />
        </NavLink>
      </div>
    </header>
  );
};
