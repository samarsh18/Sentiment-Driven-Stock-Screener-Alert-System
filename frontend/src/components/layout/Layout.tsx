import React from 'react';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';
import { useDemoUser } from '../../hooks/useUser';

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { userId } = useDemoUser();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar userId={userId} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
          {children}
        </main>
      </div>
    </div>
  );
};
