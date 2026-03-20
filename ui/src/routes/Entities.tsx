import { useEffect, useState, useMemo } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchGraph } from '@/api/client';
import type { GraphNode } from '@/types/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';
import { ENTITY_TYPE_COLORS, RETENTION_COLORS } from '@/lib/colors';
import { ArrowUpDown } from 'lucide-react';

type SortKey = 'label' | 'type' | 'created_at';
type SortDir = 'asc' | 'desc';

export default function Entities() {
  const { scope, setLastUpdated } = useAppContext();
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
        const data = await fetchGraph(scope);
        if (!cancelled) {
          setNodes(data.nodes.filter(n => n.type !== 'Episodic'));
          setLastUpdated(new Date());
          setLoading(false);
        }
      } catch { if (!cancelled) { setError("Could not reach API — is `recall ui` running?"); setLoading(false); } }
    };
    load();
    const iv = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [scope, setLastUpdated]);

  const entityTypes = useMemo(() => ['all', ...Array.from(new Set(nodes.map(n => n.type)))], [nodes]);

  const filtered = useMemo(() => {
    let result = typeFilter === 'all' ? nodes : nodes.filter(n => n.type === typeFilter);
    result = [...result].sort((a, b) => {
      const av = a[sortKey === 'created_at' ? 'id' : sortKey] ?? '';
      const bv = b[sortKey === 'created_at' ? 'id' : sortKey] ?? '';
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    return result;
  }, [nodes, typeFilter, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

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

  if (nodes.length === 0) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ backgroundColor: '#0f172a' }}>
      <h2 className="text-base font-semibold text-white">No entities found.</h2>
      <p className="text-slate-400 text-sm">No entities match the current scope and filters.</p>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#0f172a' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b flex-shrink-0" style={{ borderColor: '#334155' }}>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="h-7 w-36 text-xs bg-slate-800 border-slate-700 text-slate-200">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent className="bg-slate-800 border-slate-700">
            {entityTypes.map(t => (
              <SelectItem key={t} value={t} className="text-xs text-slate-200">{t === 'all' ? 'All types' : t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-xs text-slate-400 ml-auto">{filtered.length} entities</span>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: '#334155' }}>
              <TableHead className="text-xs text-slate-400 cursor-pointer" onClick={() => toggleSort('label')}>
                <div className="flex items-center gap-1">Name <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead className="text-xs text-slate-400 cursor-pointer" onClick={() => toggleSort('type')}>
                <div className="flex items-center gap-1">Type <ArrowUpDown size={10} /></div>
              </TableHead>
              <TableHead className="text-xs text-slate-400">Status</TableHead>
              <TableHead className="text-xs text-slate-400">Scope</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map(node => (
              <TableRow
                key={node.id}
                className="cursor-pointer hover:bg-slate-700/50 border-slate-700"
                style={{ backgroundColor: '#0f172a' }}
                onClick={() => setPanelItem({ itemType: 'entity', itemId: node.id, label: node.label })}
              >
                <TableCell className="text-sm text-slate-200 font-medium">{node.label}</TableCell>
                <TableCell>
                  <Badge className="text-xs" style={{
                    backgroundColor: `${ENTITY_TYPE_COLORS[node.type] ?? '#94a3b8'}22`,
                    color: ENTITY_TYPE_COLORS[node.type] ?? '#94a3b8',
                    border: 'none',
                  }}>
                    {node.type}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge className="text-xs" style={{ backgroundColor: `${RETENTION_COLORS.Normal}22`, color: RETENTION_COLORS.Normal, border: 'none' }}>
                    Normal
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-slate-400">{node.scope}</TableCell>
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
