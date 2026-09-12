import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Bookmark, Bell, Settings, Activity } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { to: '/watchlist', label: 'Watchlist', icon: <Bookmark className="w-4 h-4" /> },
    { to: '/alerts', label: 'Alerts', icon: <Bell className="w-4 h-4" /> },
    { to: '/settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <aside className="hidden md:flex flex-col w-64 bg-surface border-r border-surface-border p-4 space-y-6 shrink-0">
      <div className="flex items-center space-x-2 px-2 py-1">
        <div className="p-1.5 bg-accent-blue/10 text-accent-blue rounded-lg">
          <Activity className="w-5 h-5" />
        </div>
        <span className="text-sm font-bold text-white tracking-tight">StockScreener AI</span>
      </div>

      <nav className="space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
                isActive
                  ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/20'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-surface-hover'
              }`
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto p-3 bg-surface-hover rounded-xl border border-surface-border text-xs space-y-1">
        <p className="font-semibold text-gray-300">Pipeline Active</p>
        <p className="text-[11px] text-gray-500">GDELT + FinBERT + Gemini + Event Study</p>
      </div>
    </aside>
  );
};
