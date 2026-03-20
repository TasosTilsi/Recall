import { useEffect, useState, useCallback } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchGraph } from '@/api/client';
import type { GraphData } from '@/types/api';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { GraphLegend } from '@/components/graph/GraphLegend';
import { Toggle } from '@/components/ui/toggle';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Skeleton } from '@/components/ui/skeleton';

export default function GraphView() {
  const { scope, setLastUpdated } = useAppContext();
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEpisodes, setShowEpisodes] = useState(false);
  const [colorMode, setColorMode] = useState<'type' | 'scope'>('type');
  const [selectedNode, setSelectedNode] = useState<{ id: string; label: string; type: string } | null>(null);

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
    setSelectedNode(nodeData);
  }, []);

  // Suppress unused variable warning — selectedNode is stored for future detail panel use
  void selectedNode;

  if (loading) {
    return (
      <div className="flex-1 relative" style={{ backgroundColor: '#0f172a' }}>
        <Skeleton className="absolute inset-0 m-4 rounded-lg bg-slate-800" />
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-slate-500 text-sm">Loading graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: '#0f172a' }}>
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 relative" style={{ backgroundColor: '#0f172a' }}>
      {/* Graph toolbar */}
      <div
        className="flex items-center gap-3 px-4 py-2 flex-shrink-0 z-10"
        style={{ backgroundColor: '#334155', borderBottom: '1px solid #475569' }}
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

      {/* Graph canvas — fills remaining height */}
      <div className="flex-1 min-h-0 relative">
        <GraphCanvas
          nodes={data?.nodes ?? []}
          edges={data?.edges ?? []}
          showEpisodes={showEpisodes}
          colorMode={colorMode}
          onNodeClick={handleNodeClick}
        />
        <GraphLegend colorMode={colorMode} />
      </div>
    </div>
  );
}
