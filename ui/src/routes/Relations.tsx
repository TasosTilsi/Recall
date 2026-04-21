import { useEffect, useState, useMemo } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchGraph } from '@/api/client';
import type { GraphEdge, GraphNode } from '@/types/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowUpDown } from 'lucide-react';

type SortKey = 'relationship' | 'from' | 'to';
type SortDir = 'asc' | 'desc';

export default function Relations() {
  const { setLastUpdated } = useAppContext();
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [nodeMap, setNodeMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('relationship');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchGraph();
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
  }, [setLastUpdated]);

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
      if (sortKey === 'relationship') { av = a.relationship || ''; bv = b.relationship || ''; }
      else if (sortKey === 'from') { av = resolveName(a.from_id); bv = resolveName(b.from_id); }
      else if (sortKey === 'to') { av = resolveName(a.to_id); bv = resolveName(b.to_id); }
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
      <p className="text-slate-400 text-sm">Run <code className="text-blue-400">recall index</code> to populate the graph.</p>
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
                onClick={() => toggleSort('relationship')}
              >
                <div className="flex items-center gap-1">Relationship <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead
                className="text-xs font-mono tracking-widest text-slate-500 uppercase cursor-pointer w-[28%]"
                onClick={() => toggleSort('from')}
              >
                <div className="flex items-center gap-1">From <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead
                className="text-xs font-mono tracking-widest text-slate-500 uppercase cursor-pointer w-[28%]"
                onClick={() => toggleSort('to')}
              >
                <div className="flex items-center gap-1">To <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead className="text-xs font-mono tracking-widest text-slate-500 uppercase w-[6%]">
                Status
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((edge, i) => {
              const fromName = resolveName(edge.from_id);
              const toName = resolveName(edge.to_id);
              const fromResolved = !!nodeMap[edge.from_id];
              const toResolved = !!nodeMap[edge.to_id];
              return (
                <TableRow
                  key={edge.id}
                  className="border-0"
                  style={{ backgroundColor: i % 2 === 0 ? '#0b1326' : '#0f172a' }}
                >
                  <TableCell className="text-sm text-slate-200 py-3 pr-4">
                    <span className="line-clamp-2 leading-relaxed">{edge.relationship || '—'}</span>
                  </TableCell>
                  <TableCell className="py-3 pr-4">
                    <span
                      className="text-xs font-medium truncate block max-w-[180px]"
                      style={{ color: fromResolved ? '#7bd0ff' : '#64748b' }}
                      title={edge.from_id}
                    >
                      {fromName}
                    </span>
                  </TableCell>
                  <TableCell className="py-3 pr-4">
                    <span
                      className="text-xs font-medium truncate block max-w-[180px]"
                      style={{ color: toResolved ? '#7bd0ff' : '#64748b' }}
                      title={edge.to_id}
                    >
                      {toName}
                    </span>
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
    </div>
  );
}
