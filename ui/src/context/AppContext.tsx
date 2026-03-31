import React, { createContext, useContext, useState } from 'react';

interface AppContextType {
  scope: 'project' | 'global';
  setScope: (s: 'project' | 'global') => void;
  showHistory: boolean;
  setShowHistory: (v: boolean) => void;
  lastUpdated: Date | null;
  setLastUpdated: (d: Date) => void;
}

const AppContext = createContext<AppContextType>({} as AppContextType);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [scope, setScope] = useState<'project' | 'global'>('project');
  const [showHistory, setShowHistory] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  return (
    <AppContext.Provider value={{ scope, setScope, showHistory, setShowHistory, lastUpdated, setLastUpdated }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  return useContext(AppContext);
}
