import { useEffect, useState, useCallback, useRef } from 'react';
import { fetchGraph } from '@/api/client';
import type { GraphData } from '@/types/api';
import { ENTITY_TYPE_COLORS } from '@/lib/colors';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { GraphLegend } from '@/components/graph/GraphLegend';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';
import { Skeleton } from '@/components/ui/skeleton';
import Sigma from 'sigma';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

const ALL_TYPES = Object.keys(ENTITY_TYPE_COLORS);

export default function GraphView() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // selectedTypes: empty array = show all; non-empty = show only these types
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedNode, setSelectedNode] = useState<PanelItem | null>(null);
  const rendererRef = useRef<Sigma | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const result = await fetchGraph();
        if (!cancelled) {
          setData(result);
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
    const interval = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const toggleType = useCallback((type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
  }, []);

  const handleNodeClick = useCallback((nodeData: { id: string; label: string; type: string }) => {
    setSelectedNode({ itemType: 'entity', itemId: nodeData.id, label: nodeData.label });
  }, []);

  const handleRendererReady = useCallback((r: Sigma) => {
    rendererRef.current = r;
  }, []);

  if (loading) {
    return (
      <div className="flex-1 relative" style={{ backgroundColor: '#0b1326' }}>
        <Skeleton className="absolute inset-0 m-4 rounded-lg bg-slate-800" />
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-slate-500 text-sm">Loading graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: '#0b1326' }}>
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 relative" style={{ backgroundColor: '#0b1326' }}>
      {/* Graph toolbar — entity-type multi-select filter */}
      <div
        className="flex items-center gap-2 px-4 py-2 flex-shrink-0 z-10 flex-wrap"
        style={{ backgroundColor: '#171f33' }}
      >
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mr-1">Filter:</span>
        {ALL_TYPES.map(type => {
          const active = selectedTypes.length === 0 || selectedTypes.includes(type);
          const color = ENTITY_TYPE_COLORS[type];
          return (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className="flex items-center gap-1.5 text-xs h-7 px-2.5 rounded transition-all"
              style={{
                backgroundColor: active ? `${color}22` : 'transparent',
                color: active ? color : '#475569',
                border: `1px solid ${active ? color : '#334155'}`,
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: active ? color : '#475569' }} />
              {type.replace('_', ' ')}
            </button>
          );
        })}
        <button
          onClick={() => setSelectedTypes([])}
          className="text-xs h-7 px-2 text-slate-500 hover:text-slate-300 transition-colors ml-1"
        >
          Clear
        </button>
        <span className="text-xs text-slate-400 ml-auto">
          {data?.nodes.length ?? 0} nodes · {data?.edges.length ?? 0} edges
        </span>
      </div>

      {/* Detail panel — slides in from right when a node is clicked */}
      <DetailPanel item={selectedNode} onClose={() => setSelectedNode(null)} />

      {/* Graph canvas — fills remaining height */}
      <div className="flex-1 min-h-0 relative">
        <GraphCanvas
          nodes={data?.nodes ?? []}
          edges={data?.edges ?? []}
          selectedTypes={selectedTypes}
          onNodeClick={handleNodeClick}
          onRendererReady={handleRendererReady}
        />
        <GraphLegend />
        {/* Zoom controls */}
        <div className="absolute bottom-4 right-4 z-10 flex flex-col rounded-lg overflow-hidden"
             style={{ backgroundColor: 'rgba(34,42,61,0.88)', backdropFilter: 'blur(12px)' }}>
          <button
            onClick={() => rendererRef.current?.getCamera().animatedZoom({ duration: 200 })}
            className="w-8 h-8 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-700/50 transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => rendererRef.current?.getCamera().animatedUnzoom({ duration: 200 })}
            className="w-8 h-8 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-700/50 transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => rendererRef.current?.getCamera().animatedReset({ duration: 200 })}
            className="w-8 h-8 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-700/50 transition-colors"
            title="Fit to screen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
