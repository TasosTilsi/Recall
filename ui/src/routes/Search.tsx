import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAppContext } from '@/context/AppContext';
import { fetchSearch } from '@/api/client';
import type { SearchResults, SearchEntityResult } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';
import { ENTITY_TYPE_COLORS } from '@/lib/colors';

export default function Search() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  // scope is not used in v3.0 API — fetchSearch takes only query
  useAppContext();
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
        const data = await fetchSearch(q);
        if (!cancelled) {
          setResults(data);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError("Could not reach API — is `recall ui` running?");
          setLoading(false);
        }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [q]);

  // Escape key: go back
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') navigate(-1);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [navigate]);

  const hasResults = results && results.entities.length > 0;

  return (
    <div className="flex-1 overflow-auto p-8" style={{ backgroundColor: '#0b1326' }}>
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
            <p className="text-slate-400 text-sm">Try a different search term.</p>
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
                <ul className="space-y-1">
                  {results.entities.map((entity: SearchEntityResult) => (
                    <li
                      key={entity.id}
                      className="flex items-start gap-3 px-4 py-3 rounded-md cursor-pointer hover:bg-[#131b2e] transition-colors"
                      onClick={() => setPanelItem({ itemType: 'entity', itemId: entity.id, label: entity.name })}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-slate-200">{entity.name}</span>
                          <Badge className="text-[10px] h-4 uppercase tracking-widest px-1.5" style={{
                            backgroundColor: `${ENTITY_TYPE_COLORS[entity.type] ?? '#888888'}15`,
                            color: ENTITY_TYPE_COLORS[entity.type] ?? '#888888',
                            border: 'none',
                          }}>
                            {entity.type}
                          </Badge>
                        </div>
                        {entity.content_snippet && (
                          <p className="text-xs text-slate-500 mt-1 line-clamp-2">{entity.content_snippet}</p>
                        )}
                      </div>
                    </li>
                  ))}
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
