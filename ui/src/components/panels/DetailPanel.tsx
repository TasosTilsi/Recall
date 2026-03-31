import { useState, useCallback, useEffect } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbSeparator } from '@/components/ui/breadcrumb';
import { Skeleton } from '@/components/ui/skeleton';
import { X } from 'lucide-react';
import { fetchDetail } from '@/api/client';
import { useAppContext } from '@/context/AppContext';
import type { DetailRecord } from '@/types/api';
import { EntityPanel } from './EntityPanel';
import { EdgePanel } from './EdgePanel';
import { EpisodePanel } from './EpisodePanel';

export type PanelItem = { itemType: 'entity' | 'edge' | 'episode'; itemId: string; label: string };

interface DetailPanelProps {
  item: PanelItem | null;
  onClose: () => void;
  onNavigate?: (item: PanelItem) => void;
}

export function DetailPanel({ item, onClose }: DetailPanelProps) {
  const { scope } = useAppContext();
  const [breadcrumb, setBreadcrumb] = useState<PanelItem[]>([]);
  const [currentItem, setCurrentItem] = useState<PanelItem | null>(null);
  const [data, setData] = useState<DetailRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // When item prop changes (fresh open from canvas/table), reset breadcrumb
  useEffect(() => {
    if (!item) return;
    setBreadcrumb([item]);
    setCurrentItem(item);
  }, [item]);

  // Fetch data when currentItem changes
  useEffect(() => {
    if (!currentItem) return;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchDetail(currentItem.itemType, currentItem.itemId, scope);
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError('Could not load detail.');
          setLoading(false);
        }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [currentItem, scope]);

  // In-panel navigation: append to breadcrumb
  const navigateInPlace = useCallback((next: PanelItem) => {
    setBreadcrumb(prev => [...prev, next]);
    setCurrentItem(next);
  }, []);

  // Breadcrumb ancestor click: navigate back
  const navigateToBreadcrumb = useCallback((index: number) => {
    setBreadcrumb(prev => prev.slice(0, index + 1));
    setCurrentItem(breadcrumb[index]);
  }, [breadcrumb]);

  if (!item) return null;

  return (
    <div
      className="fixed right-0 top-0 h-full z-20 flex flex-col transition-all"
      style={{
        width: '420px',
        backgroundColor: '#131b2e',
        boxShadow: '-8px 0 32px rgba(0,0,0,0.5)',
        animation: 'slideIn 250ms cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      <style>{`
        @keyframes slideIn { from { transform: translateX(400px); } to { transform: translateX(0); } }
      `}</style>

      {/* Panel header: breadcrumb + close */}
      <div className="flex items-center gap-2 px-6 py-4 flex-shrink-0">
        <Breadcrumb className="flex-1 min-w-0">
          <BreadcrumbList>
            {breadcrumb.map((crumb, i) => (
              <BreadcrumbItem key={i}>
                {i < breadcrumb.length - 1 ? (
                  <>
                    <BreadcrumbLink
                      href="#"
                      onClick={(e) => { e.preventDefault(); navigateToBreadcrumb(i); }}
                      className="text-xs text-slate-400 hover:text-white truncate max-w-[80px]"
                    >
                      {crumb.label}
                    </BreadcrumbLink>
                    <BreadcrumbSeparator />
                  </>
                ) : (
                  <span className="text-xs text-white truncate max-w-[120px]">{crumb.label}</span>
                )}
              </BreadcrumbItem>
            ))}
          </BreadcrumbList>
        </Breadcrumb>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-7 w-7 text-slate-400 hover:text-white flex-shrink-0"
          title="Close"
        >
          <X size={14} />
        </Button>
      </div>

      {/* Panel content */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {loading && (
            <div className="space-y-3">
              <Skeleton className="h-6 w-3/4 bg-slate-700" />
              <Skeleton className="h-4 w-1/2 bg-slate-700" />
              <Skeleton className="h-24 bg-slate-700" />
              <Skeleton className="h-4 w-full bg-slate-700" />
              <Skeleton className="h-4 w-full bg-slate-700" />
            </div>
          )}
          {error && <p className="text-red-400 text-sm">{error}</p>}
          {!loading && !error && data && currentItem?.itemType === 'entity' && (
            <EntityPanel entity={data as import('@/types/api').DetailEntity} onNavigate={navigateInPlace} />
          )}
          {!loading && !error && data && currentItem?.itemType === 'edge' && (
            <EdgePanel edge={data as import('@/types/api').DetailEdge} onNavigate={navigateInPlace} />
          )}
          {!loading && !error && data && currentItem?.itemType === 'episode' && (
            <EpisodePanel episode={data as import('@/types/api').DetailEpisode} onNavigate={navigateInPlace} />
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
