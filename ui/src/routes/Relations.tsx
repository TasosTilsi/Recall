import { useEffect, useState, useMemo } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchGraph } from '@/api/client';
import type { GraphEdge, GraphNode } from '@/types/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';
import { ArrowUpDown } from 'lucide-react';

type SortKey = 'fact' | 'from' | 'to';
type SortDir = 'asc' | 'desc';

export default function Relations() {
  const { scope, setLastUpdated } = useAppContext();
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [nodeMap, setNodeMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [panelItem, setPanelItem] = useState<PanelItem | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('fact');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchGraph(scope);
        if (!cancelled) {
          const map: Record<string, string> = {};
          (data.nodes as GraphNode[]).forEach(n => { map[n.id] = n.label; });
          setNodeMap(map);
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

  const resolveName = (uuid: string) =>
    nodeMap[uuid] || uuid.slice(0, 8) + '…';

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const sorted = useMemo(() => {
    return [...edges].sort((a, b) => {
      let av = '';
      let bv = '';
      if (sortKey === 'fact') { av = a.name || ''; bv = b.name || ''; }
      else if (sortKey === 'from') { av = resolveName(a.source); bv = resolveName(b.source); }
      else if (sortKey === 'to') { av = resolveName(a.target); bv = resolveName(b.target); }
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });
  }, [edges, nodeMap, sortKey, sortDir]);

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
      <p className="text-slate-400 text-sm">No relationships match the current scope.</p>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#0f172a' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b flex-shrink-0" style={{ borderColor: '#1e293b' }}>
        <span className="text-xs text-slate-400 ml-auto">{edges.length} relations</span>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: '#131b2e' }}>
              <TableHead
                className="text-xs font-mono tracking-widest text-slate-500 uppercase cursor-pointer w-[38%]"
                onClick={() => toggleSort('fact')}
              >
                <div className="flex items-center gap-1">Fact <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead
                className="text-xs font-mono tracking-widest text-slate-500 uppercase cursor-pointer w-[17%]"
                onClick={() => toggleSort('from')}
              >
                <div className="flex items-center gap-1">From <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead
                className="text-xs font-mono tracking-widest text-slate-500 uppercase cursor-pointer w-[17%]"
                onClick={() => toggleSort('to')}
              >
                <div className="flex items-center gap-1">To <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead className="text-xs font-mono tracking-widest text-slate-500 uppercase w-[12%]">
                Valid From
              </TableHead>
              <TableHead className="text-xs font-mono tracking-widest text-slate-500 uppercase w-[12%]">
                Valid Until
              </TableHead>
              <TableHead className="text-xs font-mono tracking-widest text-slate-500 uppercase w-[8%]">
                Status
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((edge, i) => {
              const fromName = resolveName(edge.source);
              const toName = resolveName(edge.target);
              const isResolved = nodeMap[edge.source] && nodeMap[edge.target];
              return (
                <TableRow
                  key={edge.id}
                  className="cursor-pointer border-0 group"
                  style={{ backgroundColor: i % 2 === 0 ? '#0b1326' : '#0f172a' }}
                  onClick={() => setPanelItem({ itemType: 'edge', itemId: edge.id, label: edge.name || 'Edge' })}
                >
                  <TableCell className="text-sm text-slate-200 py-3 pr-4 group-hover:text-white transition-colors">
                    <span className="line-clamp-2 leading-relaxed">{edge.name || '—'}</span>
                  </TableCell>
                  <TableCell className="py-3 pr-4">
                    <span
                      className="text-xs font-medium truncate block max-w-[140px]"
                      style={{ color: isResolved ? '#7bd0ff' : '#64748b' }}
                      title={edge.source}
                    >
                      {fromName}
                    </span>
                  </TableCell>
                  <TableCell className="py-3 pr-4">
                    <span
                      className="text-xs font-medium truncate block max-w-[140px]"
                      style={{ color: isResolved ? '#7bd0ff' : '#64748b' }}
                      title={edge.target}
                    >
                      {toName}
                    </span>
                  </TableCell>
                  <TableCell className="py-3 pr-4">
                    <span className="text-xs font-mono text-slate-500">—</span>
                  </TableCell>
                  <TableCell className="py-3 pr-4">
                    <span className="text-xs font-mono text-slate-500">—</span>
                  </TableCell>
                  <TableCell className="py-3">
                    <Badge
                      className="text-xs font-mono tracking-wider"
                      style={{ backgroundColor: '#4ade8018', color: '#4ade80', border: '1px solid #4ade8030' }}
                    >
                      ACTIVE
                    </Badge>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {panelItem && <DetailPanel item={panelItem} onClose={() => setPanelItem(null)} />}
    </div>
  );
}
