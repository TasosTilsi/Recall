import { useEffect, useState } from 'react';
import { fetchWorldView } from '@/api/client';
import type { WorldViewData } from '@/types/api';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ENTITY_TYPE_COLORS } from '@/lib/colors';

export default function WorldView() {
  const [data, setData] = useState<WorldViewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await fetchWorldView();
        setData(result);
      } catch (err) {
        setError("Could not reach API — is `recall ui` running?");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0b1326' }}>
        <Skeleton className="h-48 rounded-lg bg-slate-800 mb-6" />
        <Skeleton className="h-96 rounded-lg bg-slate-800" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: '#0b1326' }}>
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  if (!data || data.repositories.length <= 1) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ backgroundColor: '#0b1326' }}>
        <h2 className="text-base font-semibold text-white">No other repositories detected.</h2>
        <p className="text-slate-400 text-sm max-w-md text-center">
          World View automatically connects sibling repositories in the same parent directory that have been indexed with <code className="text-blue-400">recall</code>.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0b1326' }}>
      <h1 className="text-xl font-bold text-white mb-6">World View</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="p-5 md:col-span-1" style={{ backgroundColor: '#222a3d', border: 'none' }}>
          <h2 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-4">Workspace Repositories</h2>
          <div className="space-y-3">
            {data.repositories.map(repo => (
              <div key={repo.name} className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-400"></div>
                <span className="text-sm font-medium text-slate-200">{repo.name}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5 md:col-span-2" style={{ backgroundColor: '#222a3d', border: 'none' }}>
          <h2 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-4">Bridge Nodes</h2>
          <p className="text-xs text-slate-400 mb-4 italic">
            Entities identified across multiple repositories. These serve as conceptual links between your projects.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {data.bridge_nodes.map(bridge => (
              <div key={bridge.name} className="p-3 rounded-md bg-[#171f33] border border-slate-700/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-white">{bridge.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded uppercase font-bold" style={{ backgroundColor: ENTITY_TYPE_COLORS[bridge.occurrences[0].type] + '33', color: ENTITY_TYPE_COLORS[bridge.occurrences[0].type] }}>
                    {bridge.occurrences[0].type}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {bridge.occurrences.map(occ => (
                    <span key={occ.repo} className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">
                      {occ.repo}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {data.bridge_nodes.length === 0 && (
              <p className="text-sm text-slate-500 italic">No identical concepts found across repos yet.</p>
            )}
          </div>
        </Card>
      </div>

      <Card className="p-6" style={{ backgroundColor: '#222a3d', border: 'none' }}>
        <h2 className="text-sm font-semibold text-white mb-4">World Map (Preview)</h2>
        <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-slate-700 rounded-lg">
           <p className="text-slate-500 text-sm">Visual graph representation of repo interconnections coming soon.</p>
           <p className="text-slate-600 text-[10px] mt-2 italic">Identified {data.bridge_nodes.length} bridge points across {data.repositories.length} repos.</p>
        </div>
      </Card>
    </div>
  );
}
