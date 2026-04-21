import { useEffect, useState, useMemo } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchGraph } from '@/api/client';
import type { GraphNode } from '@/types/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';
import { ENTITY_TYPE_COLORS } from '@/lib/colors';
import { ArrowUpDown } from 'lucide-react';

type SortKey = 'label' | 'type';
type SortDir = 'asc' | 'desc';

export default function Entities() {
  const { setLastUpdated } = useAppContext();
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [sortKey, setSortKey] = useState<SortKey>('label');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [panelItem, setPanelItem] = useState<PanelItem | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchGraph();
        if (!cancelled) {
          setNodes(data.nodes);
          setLastUpdated(new Date());
          setLoading(false);
        }
      } catch { if (!cancelled) { setError("Could not reach API — is `recall ui` running?"); setLoading(false); } }
    };
    load();
    const iv = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [setLastUpdated]);

  const entityTypes = useMemo(() => ['all', ...Array.from(new Set(nodes.map(n => n.type)))], [nodes]);

  const filtered = useMemo(() => {
    let result = typeFilter === 'all' ? nodes : nodes.filter(n => n.type === typeFilter);
    result = [...result].sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    return result;
  }, [nodes, typeFilter, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  if (loading) return (
    <div className="flex-1 p-6" style={{ backgroundColor: '#0b1326' }}>
      {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-12 rounded bg-slate-800 mb-2" />)}
    </div>
  );

  if (error) return (
    <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: '#0b1326' }}>
      <p className="text-red-400 text-sm">{error}</p>
    </div>
  );

  if (nodes.length === 0) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ backgroundColor: '#0b1326' }}>
      <h2 className="text-base font-semibold text-white">No entities found.</h2>
      <p className="text-slate-400 text-sm">Run <code className="text-blue-400">recall index</code> to populate entities.</p>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#0b1326' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-4 flex-shrink-0 bg-[#0b1326]">
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="h-8 w-40 text-xs bg-[#131b2e] border-none text-slate-300 hover:bg-[#171f33] transition-colors">
            <SelectValue placeholder="Entity Type" />
          </SelectTrigger>
          <SelectContent className="bg-[#131b2e] border-none text-slate-200 shadow-2xl">
            {entityTypes.map(t => (
              <SelectItem key={t} value={t} className="text-xs hover:bg-[#171f33] focus:bg-[#171f33]">{t === 'all' ? 'All Types' : t}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <span className="text-xs text-slate-400 ml-auto">{filtered.length} entities</span>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: '#222a3d' }}>
              <TableHead className="text-xs text-slate-400 cursor-pointer" onClick={() => toggleSort('label')}>
                <div className="flex items-center gap-1">Name <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead className="text-xs text-slate-400 cursor-pointer" onClick={() => toggleSort('type')}>
                <div className="flex items-center gap-1">Type <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead className="text-xs text-slate-400">Commit SHA</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map(node => (
              <TableRow
                key={node.id}
                className="group cursor-pointer hover:bg-[#131b2e] transition-colors border-none"
                style={{ backgroundColor: '#0b1326' }}
                onClick={() => setPanelItem({ itemType: 'entity', itemId: node.id, label: node.label })}
              >
                <TableCell className="text-sm text-slate-200 font-medium py-4">{node.label}</TableCell>
                <TableCell>
                  <Badge className="text-xs" style={{
                    backgroundColor: `${ENTITY_TYPE_COLORS[node.type] ?? '#888888'}22`,
                    color: ENTITY_TYPE_COLORS[node.type] ?? '#888888',
                    border: 'none',
                  }}>
                    {node.type}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-slate-400 font-mono">{node.commit_sha ? node.commit_sha.slice(0, 8) : '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Detail panel overlay */}
      {panelItem && (
        <DetailPanel item={panelItem} onClose={() => setPanelItem(null)} />
      )}
    </div>
  );
}
