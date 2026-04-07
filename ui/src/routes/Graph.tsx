import { useEffect, useState, useCallback, useRef } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchGraph } from '@/api/client';
import type { GraphData } from '@/types/api';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { GraphLegend } from '@/components/graph/GraphLegend';
import { DetailPanel, type PanelItem } from '@/components/panels/DetailPanel';
import { Toggle } from '@/components/ui/toggle';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Skeleton } from '@/components/ui/skeleton';
import Sigma from 'sigma';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

export default function GraphView() {
  const { scope, setLastUpdated } = useAppContext();
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEpisodes, setShowEpisodes] = useState(false);
  const [colorMode, setColorMode] = useState<'type' | 'scope'>('type');
  const [selectedNode, setSelectedNode] = useState<PanelItem | null>(null);
  const rendererRef = useRef<Sigma | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const result = await fetchGraph(scope);
        if (!cancelled) {
          setData(result);
          setLastUpdated(new Date());
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
  }, [scope, setLastUpdated]);

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
      {/* Graph toolbar */}
      <div
        className="flex items-center gap-3 px-4 py-2 flex-shrink-0 z-10"
        style={{ backgroundColor: '#171f33' }}
      >
        <Toggle
          pressed={showEpisodes}
          onPressedChange={setShowEpisodes}
          className="text-xs h-7 px-3 data-[state=on]:bg-blue-500 data-[state=on]:text-white"
        >
          Show episodes
        </Toggle>
        <ToggleGroup
          type="single"
          value={colorMode}
          onValueChange={(v) => v && setColorMode(v as 'type' | 'scope')}
        >
          <ToggleGroupItem value="type" className="text-xs h-7 px-2">By type</ToggleGroupItem>
          <ToggleGroupItem value="scope" className="text-xs h-7 px-2">By scope</ToggleGroupItem>
        </ToggleGroup>
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
          showEpisodes={showEpisodes}
          colorMode={colorMode}
          onNodeClick={handleNodeClick}
          onRendererReady={handleRendererReady}
        />
        <GraphLegend colorMode={colorMode} />
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
