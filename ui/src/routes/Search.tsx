import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAppContext } from '@/context/AppContext';
import { fetchSearch } from '@/api/client';
import type { SearchResults } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';
import { ENTITY_TYPE_COLORS, SOURCE_COLORS } from '@/lib/colors';

export default function Search() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { scope } = useAppContext();
  const q = searchParams.get('q') ?? '';

  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panelItem, setPanelItem] = useState<PanelItem | null>(null);

  useEffect(() => {
    if (!q.trim()) return;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchSearch(q, scope);
        if (!cancelled) {
          setResults(data);
          setLoading(false);
        }
      } catch (e) {
        if (!cancelled) {
          setError("Could not reach API — is `recall ui` running?");
          setLoading(false);
        }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [q, scope]);

  // Escape key: go back
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') navigate(-1);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [navigate]);

  const hasResults = results && (
    results.entities.length > 0 || results.relations.length > 0 || results.episodes.length > 0
  );

  return (
    <div className="flex-1 overflow-auto p-6" style={{ backgroundColor: '#0f172a' }}>
      <div className="max-w-3xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-base font-semibold text-white">
            {q ? `Search results for "${q}"` : 'Search'}
          </h1>
          <span className="text-xs text-slate-500">Press Esc to go back</span>
        </div>

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {[0, 1, 2].map(i => <Skeleton key={i} className="h-16 rounded bg-slate-800" />)}
          </div>
        )}

        {/* Error */}
        {error && <p className="text-red-400 text-sm">{error}</p>}

        {/* No results */}
        {!loading && !error && q && !hasResults && results && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <h2 className="text-base font-semibold text-white">No results for "{q}".</h2>
            <p className="text-slate-400 text-sm">Try a different search term or switch scope.</p>
          </div>
        )}

        {/* Empty query */}
        {!q && (
          <p className="text-slate-500 text-sm">Type in the search bar and press Enter to search.</p>
        )}

        {/* Results */}
        {!loading && !error && results && hasResults && (
          <div className="space-y-8">
            {/* Entities */}
            {results.entities.length > 0 && (
              <section>
                <h2 className="text-sm font-semibold text-slate-400 mb-3">
                  Entities ({results.entities.length})
                </h2>
                <ul className="space-y-2">
                  {results.entities.map(entity => (
                    <li
                      key={entity.id}
                      className="flex items-start gap-3 p-3 rounded-lg cursor-pointer hover:bg-slate-800 border border-slate-700/50 transition-colors"
                      onClick={() => setPanelItem({ itemType: 'entity', itemId: entity.id, label: entity.label })}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-white font-medium">{entity.label}</span>
                          <Badge className="text-xs" style={{
                            backgroundColor: `${ENTITY_TYPE_COLORS[entity.type] ?? '#94a3b8'}22`,
                            color: ENTITY_TYPE_COLORS[entity.type] ?? '#94a3b8',
                            border: 'none',
                          }}>
                            {entity.type}
                          </Badge>
                        </div>
                        {entity.summary && (
                          <p className="text-xs text-slate-400 mt-1 truncate">{entity.summary}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* Relations */}
            {results.relations.length > 0 && (
              <section>
                <h2 className="text-sm font-semibold text-slate-400 mb-3">
                  Relations ({results.relations.length})
                </h2>
                <ul className="space-y-2">
                  {results.relations.map(rel => (
                    <li
                      key={rel.id}
                      className="p-3 rounded-lg cursor-pointer hover:bg-slate-800 border border-slate-700/50 transition-colors"
                      onClick={() => setPanelItem({ itemType: 'edge', itemId: rel.id, label: rel.label || rel.fact?.slice(0, 40) || 'Edge' })}
                    >
                      <p className="text-sm text-white">{rel.fact || rel.label || 'Relation'}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        {rel.source} → {rel.target}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* Episodes */}
            {results.episodes.length > 0 && (
              <section>
                <h2 className="text-sm font-semibold text-slate-400 mb-3">
                  Episodes ({results.episodes.length})
                </h2>
                <ul className="space-y-2">
                  {results.episodes.map(ep => {
                    const src = ep.source || 'cli-add';
                    const srcColor = SOURCE_COLORS[src] ?? '#94a3b8';
                    return (
                      <li
                        key={ep.uuid}
                        className="flex items-start gap-3 p-3 rounded-lg cursor-pointer hover:bg-slate-800 border border-slate-700/50 transition-colors"
                        onClick={() => setPanelItem({ itemType: 'episode', itemId: ep.uuid, label: ep.source_description || ep.name })}
                      >
                        <Badge style={{ backgroundColor: `${srcColor}22`, color: srcColor, border: `1px solid ${srcColor}44`, flexShrink: 0 }}>
                          {src}
                        </Badge>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white truncate">{ep.source_description || ep.name}</p>
                          <p className="text-xs text-slate-500">{ep.created_at?.slice(0, 16) ?? ''}</p>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            )}
          </div>
        )}
      </div>

      {panelItem && <DetailPanel item={panelItem} onClose={() => setPanelItem(null)} />}
    </div>
  );
}
