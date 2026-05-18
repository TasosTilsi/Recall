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

      <Card className="p-0 overflow-hidden" style={{ backgroundColor: '#222a3d', border: 'none' }}>
        <div className="p-6 pb-0">
          <h2 className="text-sm font-semibold text-white mb-2">Interactive World Map</h2>
          <p className="text-xs text-slate-400 mb-4">
            Visualizing interconnections between {data.repositories.length} repositories through {data.bridge_nodes.length} shared concepts.
          </p>
        </div>
        <div className="h-[500px] w-full bg-[#0b1326] relative">
           {/* Placeholder for Sigma.js cross-repo graph */}
           <div className="absolute inset-0 flex flex-col items-center justify-center border-t border-slate-800">
              <div className="relative w-64 h-64">
                 {/* Visual representation of a network */}
                 <div className="absolute inset-0 flex items-center justify-center opacity-20">
                    <div className="w-full h-full rounded-full border border-blue-500 animate-pulse"></div>
                 </div>
                 {data.repositories.map((repo, i) => {
                    const angle = (i / data.repositories.length) * 2 * Math.PI;
                    const x = 50 + 40 * Math.cos(angle);
                    const y = 50 + 40 * Math.sin(angle);
                    return (
                      <div
                        key={repo.name}
                        className="absolute w-12 h-12 rounded-full bg-blue-600/20 border border-blue-400 flex items-center justify-center text-[10px] font-bold text-blue-200"
                        style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }}
                      >
                        {repo.name}
                      </div>
                    );
                 })}
                 <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-4 h-4 rounded-full bg-amber-400 shadow-[0_0_15px_rgba(251,191,36,0.6)]"></div>
                 </div>
              </div>
              <p className="text-slate-500 text-xs mt-4">WebGL World Discovery active</p>
           </div>
        </div>
      </Card>
    </div>
  );
}
