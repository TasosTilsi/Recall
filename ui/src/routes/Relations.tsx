import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchGraph } from '@/api/client';
import type { GraphEdge } from '@/types/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';

export default function Relations() {
  const { scope, setLastUpdated } = useAppContext();
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [panelItem, setPanelItem] = useState<PanelItem | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchGraph(scope);
        if (!cancelled) {
          setEdges(data.edges);
          setLastUpdated(new Date());
          setLoading(false);
        }
      } catch { if (!cancelled) { setError("Could not reach API — is `recall ui` running?"); setLoading(false); } }
    };
    load();
    const iv = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [scope, setLastUpdated]);

  if (loading) return (
    <div className="flex-1 p-6" style={{ backgroundColor: '#0f172a' }}>
      {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-12 rounded bg-slate-800 mb-2" />)}
    </div>
  );

  if (error) return (
    <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: '#0f172a' }}>
      <p className="text-red-400 text-sm">{error}</p>
    </div>
  );

  if (edges.length === 0) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ backgroundColor: '#0f172a' }}>
      <h2 className="text-base font-semibold text-white">No relations found.</h2>
      <p className="text-slate-400 text-sm">No relationships match the current scope and filters.</p>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#0f172a' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b flex-shrink-0" style={{ borderColor: '#334155' }}>
        <span className="text-xs text-slate-400">{edges.length} relations</span>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: '#334155' }}>
              <TableHead className="text-xs text-slate-400">Fact</TableHead>
              <TableHead className="text-xs text-slate-400">From</TableHead>
              <TableHead className="text-xs text-slate-400">To</TableHead>
              <TableHead className="text-xs text-slate-400">Relation</TableHead>
              <TableHead className="text-xs text-slate-400">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {edges.map((edge) => (
              <TableRow
                key={edge.id}
                className="cursor-pointer hover:bg-slate-700/50 border-slate-700"
                style={{ backgroundColor: '#0f172a' }}
                onClick={() => setPanelItem({ itemType: 'edge', itemId: edge.id, label: edge.name || 'Edge' })}
              >
                <TableCell className="text-sm text-slate-200 max-w-[180px] truncate">{edge.name || '—'}</TableCell>
                <TableCell className="text-xs text-slate-400 font-mono max-w-[80px] truncate">{edge.source}</TableCell>
                <TableCell className="text-xs text-slate-400 font-mono max-w-[80px] truncate">{edge.target}</TableCell>
                <TableCell className="text-xs text-slate-400">RELATES_TO</TableCell>
                <TableCell>
                  <Badge className="text-xs" style={{ backgroundColor: '#4ade8022', color: '#4ade80', border: 'none' }}>
                    Active
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {panelItem && <DetailPanel item={panelItem} onClose={() => setPanelItem(null)} />}
    </div>
  );
}
