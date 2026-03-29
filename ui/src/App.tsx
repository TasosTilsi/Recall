import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider, useAppContext } from '@/context/AppContext';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { StatusBar } from '@/components/layout/StatusBar';
import Dashboard from '@/routes/Dashboard';
import GraphView from '@/routes/Graph';
import Entities from '@/routes/Entities';
import Relations from '@/routes/Relations';
import Episodes from '@/routes/Episodes';
import Search from '@/routes/Search';
import { useState, useCallback } from 'react';

function Shell() {
  const { setLastUpdated } = useAppContext();
  const [statusCounts] = useState({ entities: 0, edges: 0, episodes: 0 });
  const [_refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = useCallback(() => {
    setRefreshKey(k => k + 1);
    setLastUpdated(new Date());
  }, [setLastUpdated]);

  return (
    <div className="flex flex-col h-screen" style={{ backgroundColor: '#0b1326' }}>
      <Header onRefresh={handleRefresh} />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 min-h-0 overflow-hidden flex flex-col">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/graph" element={<GraphView />} />
            <Route path="/entities" element={<Entities />} />
            <Route path="/relations" element={<Relations />} />
            <Route path="/episodes" element={<Episodes />} />
            <Route path="/search" element={<Search />} />
          </Routes>
        </main>
      </div>
      <StatusBar
        entities={statusCounts.entities}
        edges={statusCounts.edges}
        episodes={statusCounts.episodes}
      />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Shell />
      </AppProvider>
    </BrowserRouter>
  );
}
