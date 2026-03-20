import { useEffect, useState, useMemo } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchDashboard } from '@/api/client';
import type { EpisodeSummary } from '@/types/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';
import { SOURCE_COLORS } from '@/lib/colors';

export default function Episodes() {
  const { scope, setLastUpdated } = useAppContext();
  const [episodes, setEpisodes] = useState<EpisodeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [panelItem, setPanelItem] = useState<PanelItem | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        // Dashboard endpoint returns recent_episodes; use it for episodes tab
        const data = await fetchDashboard(scope);
        if (!cancelled) {
          setEpisodes(data.recent_episodes);
          setLastUpdated(new Date());
          setLoading(false);
        }
      } catch { if (!cancelled) { setError("Could not reach API — is `recall ui` running?"); setLoading(false); } }
    };
    load();
    const iv = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [scope, setLastUpdated]);

  const filtered = useMemo(() => {
    if (sourceFilter === 'all') return episodes;
    return episodes.filter(ep => {
      const src = ep.source || '';
      if (sourceFilter === 'git-index') return src.toLowerCase().includes('git');
      if (sourceFilter === 'hook-capture') return src.toLowerCase().includes('hook') || src.toLowerCase().includes('capture');
      return !src.toLowerCase().includes('git') && !src.toLowerCase().includes('hook');
    });
  }, [episodes, sourceFilter]);

  if (loading) return (
    <div className="flex-1 p-6" style={{ backgroundColor: '#0f172a' }}>
      {[0, 1, 2].map(i => <Skeleton key={i} className="h-28 rounded-lg bg-slate-800 mb-3" />)}
    </div>
  );

  if (error) return (
    <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: '#0f172a' }}>
      <p className="text-red-400 text-sm">{error}</p>
    </div>
  );

  if (episodes.length === 0) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ backgroundColor: '#0f172a' }}>
      <h2 className="text-base font-semibold text-white">No episodes yet.</h2>
      <p className="text-slate-400 text-sm">Run <code className="text-blue-400">recall add 'text'</code> to capture your first episode.</p>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#0f172a' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b flex-shrink-0" style={{ borderColor: '#334155' }}>
        <Select value={sourceFilter} onValueChange={setSourceFilter}>
          <SelectTrigger className="h-7 w-36 text-xs bg-slate-800 border-slate-700 text-slate-200">
            <SelectValue placeholder="Filter source" />
          </SelectTrigger>
          <SelectContent className="bg-slate-800 border-slate-700">
            <SelectItem value="all" className="text-xs text-slate-200">All sources</SelectItem>
            <SelectItem value="git-index" className="text-xs text-slate-200">git-index</SelectItem>
            <SelectItem value="hook-capture" className="text-xs text-slate-200">hook-capture</SelectItem>
            <SelectItem value="cli-add" className="text-xs text-slate-200">cli-add</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-xs text-slate-400 ml-auto">{filtered.length} episodes</span>
      </div>

      {/* Episode cards */}
      <div className="flex-1 overflow-auto p-4 space-y-3">
        {filtered.map(ep => {
          const src = ep.source || 'cli-add';
          const srcColor = SOURCE_COLORS[src] ?? '#94a3b8';
          return (
            <Card
              key={ep.uuid}
              className="p-4 cursor-pointer transition-colors"
              style={{ backgroundColor: '#1e293b', borderColor: '#334155' }}
              onClick={() => setPanelItem({ itemType: 'episode', itemId: ep.uuid, label: ep.source_description || ep.name })}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 font-medium truncate">{ep.source_description || ep.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{ep.created_at?.slice(0, 16) ?? ''}</p>
                </div>
                <Badge style={{ backgroundColor: `${srcColor}22`, color: srcColor, border: `1px solid ${srcColor}44`, flexShrink: 0 }}>
                  {src}
                </Badge>
              </div>
            </Card>
          );
        })}
      </div>

      {panelItem && <DetailPanel item={panelItem} onClose={() => setPanelItem(null)} />}
    </div>
  );
}
