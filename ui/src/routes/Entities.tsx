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
import { ArrowUpDown, Check, ChevronsUpDown } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandGroup, CommandItem, CommandList } from '@/components/ui/command';
import { Button } from '@/components/ui/button';

type SortKey = 'label' | 'type' | 'created_at';
type SortDir = 'asc' | 'desc';

const STATUSES = ['Pinned', 'Normal', 'Stale', 'Archived'] as const;

export default function Entities() {
  const { scope, setLastUpdated } = useAppContext();
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [sortKey, setSortKey] = useState<SortKey>('label');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [panelItem, setPanelItem] = useState<PanelItem | null>(null);
  const [retentionFilter, setRetentionFilter] = useState<string[]>([]);
  const [retentionOpen, setRetentionOpen] = useState(false);

  const toggleStatus = (status: string) => {
    setRetentionFilter(prev =>
      prev.includes(status) ? prev.filter(s => s !== status) : [...prev, status]
    );
  };

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
    // Retention filter: empty = show all except Archived (default behavior)
    if (retentionFilter.length === 0) {
      result = result.filter(n => (n.retention_status ?? 'Normal') !== 'Archived');
    } else {
      result = result.filter(n => retentionFilter.includes(n.retention_status ?? 'Normal'));
    }
    result = [...result].sort((a, b) => {
      const av = a[sortKey === 'created_at' ? 'id' : sortKey] ?? '';
      const bv = b[sortKey === 'created_at' ? 'id' : sortKey] ?? '';
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    return result;
  }, [nodes, typeFilter, retentionFilter, sortKey, sortDir]);

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

        <Popover open={retentionOpen} onOpenChange={setRetentionOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" role="combobox" aria-expanded={retentionOpen}
              className="h-7 w-36 text-xs bg-slate-800 border-slate-700 text-slate-200 justify-between">
              {retentionFilter.length === 0 ? 'All statuses' : `${retentionFilter.length} selected`}
              <ChevronsUpDown className="ml-auto h-3 w-3 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-36 p-0 bg-slate-800 border-slate-700">
            <Command>
              <CommandList>
                <CommandGroup>
                  {STATUSES.map(status => (
                    <CommandItem key={status} onSelect={() => toggleStatus(status)}
                      className="text-xs text-slate-200 cursor-pointer">
                      <Check className={`mr-2 h-3 w-3 ${retentionFilter.includes(status) ? 'opacity-100' : 'opacity-0'}`} />
                      {status}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>

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
                  <Badge className="text-xs" style={{
                    backgroundColor: `${RETENTION_COLORS[node.retention_status ?? 'Normal']}22`,
                    color: RETENTION_COLORS[node.retention_status ?? 'Normal'],
                    border: 'none',
                  }}>
                    {node.retention_status ?? 'Normal'}
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
