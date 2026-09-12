import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { LoadingCard } from '../components/common/LoadingCard';
import { ErrorState } from '../components/common/ErrorState';
import { useDemoUser, useUserPreferences } from '../hooks/useUser';
import { Settings, Save, CheckCircle, ShieldCheck } from 'lucide-react';
import { USE_MOCK, API_BASE_URL } from '../api/client';

export const SettingsPage: React.FC = () => {
  const { userId, user } = useDemoUser();
  const { preferences, isLoading, error, updatePreferences, isUpdating } = useUserPreferences(userId);

  const [savedFeedback, setSavedFeedback] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (preferences) {
      updatePreferences(!preferences.is_active, {
        onSuccess: () => {
          setSavedFeedback(true);
          setTimeout(() => setSavedFeedback(false), 3000);
        },
      });
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        title="Application Settings"
        subtitle="User profile, background pipeline active status, and environment integration state"
      />

      {isLoading ? (
        <LoadingCard message="Loading user preferences..." />
      ) : error ? (
        <ErrorState title="Failed to load preferences" />
      ) : (
        <form onSubmit={handleSave} className="space-y-6">
          {/* User Profile Card */}
          <div className="bg-surface border border-surface-border p-5 rounded-xl space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center">
              <Settings className="w-4 h-4 mr-2 text-accent-blue" />
              Demo User Profile
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-mono text-gray-400 mb-1">User ID</label>
                <div className="bg-surface-hover border border-surface-border p-2.5 rounded-lg font-mono text-white">
                  #{userId}
                </div>
              </div>

              <div>
                <label className="block font-mono text-gray-400 mb-1">Registered Email</label>
                <div className="bg-surface-hover border border-surface-border p-2.5 rounded-lg text-white">
                  {user?.email || 'demo@screener.local'}
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-surface-border flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-white">Active Monitoring Service Status</p>
                <p className="text-[11px] text-gray-400">Controls whether background alert generation is active for this account</p>
              </div>

              <button
                type="button"
                onClick={() => updatePreferences(!preferences?.is_active)}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  preferences?.is_active ? 'bg-emerald-500' : 'bg-gray-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    preferences?.is_active ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Environment State Card */}
          <div className="bg-surface border border-surface-border p-5 rounded-xl space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center">
              <ShieldCheck className="w-4 h-4 mr-2 text-accent-blue" />
              System Integration Environment
            </h3>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between p-2.5 bg-surface-hover rounded-lg border border-surface-border">
                <span className="text-gray-400">REST API Base URL</span>
                <span className="text-accent-blue font-bold">{API_BASE_URL}</span>
              </div>

              <div className="flex justify-between p-2.5 bg-surface-hover rounded-lg border border-surface-border">
                <span className="text-gray-400">API Mode</span>
                <span className={USE_MOCK ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
                  {USE_MOCK ? 'MOCK FALLBACK (VITE_USE_MOCK=true)' : 'REAL FASTAPI BACKEND'}
                </span>
              </div>
            </div>
          </div>

          {savedFeedback && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center text-xs text-emerald-400">
              <CheckCircle className="w-4 h-4 mr-2 shrink-0" />
              Preferences updated successfully!
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isUpdating}
              className="inline-flex items-center px-4 py-2 bg-accent-blue text-slate-950 text-xs font-bold rounded-lg hover:bg-blue-400 transition-colors disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5 mr-1.5" />
              {isUpdating ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
