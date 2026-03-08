'use client';
import dynamic from 'next/dynamic';
import { useState, useCallback } from 'react';
import { NodeData, GraphData, fetchGraph, fetchNodeDetail, NodeDetail } from '@/lib/api';
import SearchFilter from '@/components/SearchFilter';
import NodeSidebar from '@/components/NodeSidebar';
import Legend from '@/components/Legend';

// SSR guard: react-force-graph-2d uses window/canvas — must be client-only
const GraphCanvas = dynamic(
  () => import('@/components/GraphCanvas').then(mod => ({ default: mod.GraphCanvas })),
  { ssr: false, loading: () => <p className="text-slate-400 p-8">Loading graph...</p> }
);

export default function Home() {
  const [scope, setScope] = useState<'project' | 'global'>('project');
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeDetail | null>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [colorMode, setColorMode] = useState<'type' | 'scope'>('type');
  const [layout, setLayout] = useState<'hierarchical' | 'force'>('hierarchical');

  const loadGraph = useCallback(async (s: 'project' | 'global') => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGraph(s);
      setGraphData(data);
    } catch {
      setError('Could not reach API — is `graphiti ui` running?');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load on mount
  useState(() => { loadGraph(scope); });

  const handleNodeClick = useCallback(async (node: NodeData) => {
    try {
      const detail = await fetchNodeDetail(node.id);
      setSelectedNode(detail);
    } catch { /* ignore */ }
  }, []);

  const entityTypes = Array.from(new Set((graphData?.nodes ?? []).map(n => n.entityType)));

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center gap-4 px-4 py-2 bg-slate-900 border-b border-slate-800 shrink-0">
        <span className="font-bold text-blue-400 mr-2">Graphiti</span>
        {/* Scope toggle */}
        <div className="flex rounded overflow-hidden border border-slate-700 text-sm">
          {(['project', 'global'] as const).map(s => (
            <button key={s} onClick={() => { setScope(s); loadGraph(s); }}
              className={`px-3 py-1 ${scope === s ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        {/* Layout toggle */}
        <div className="flex rounded overflow-hidden border border-slate-700 text-sm">
          {(['hierarchical', 'force'] as const).map(l => (
            <button key={l} onClick={() => setLayout(l)}
              className={`px-3 py-1 ${layout === l ? 'bg-violet-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}>
              {l.charAt(0).toUpperCase() + l.slice(1)}
            </button>
          ))}
        </div>
        {/* Color mode toggle */}
        <div className="flex rounded overflow-hidden border border-slate-700 text-sm">
          {(['type', 'scope'] as const).map(m => (
            <button key={m} onClick={() => setColorMode(m)}
              className={`px-3 py-1 ${colorMode === m ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}>
              By {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>
        <SearchFilter search={search} onSearch={setSearch}
          typeFilter={typeFilter} onTypeFilter={setTypeFilter}
          entityTypes={entityTypes} />
        <span className="ml-auto text-xs text-slate-500">
          {graphData ? `${graphData.nodes.length} nodes` : ''}
        </span>
      </header>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 relative">
          {loading && <div className="absolute inset-0 flex items-center justify-center text-slate-400">Loading...</div>}
          {error && <div className="absolute inset-0 flex items-center justify-center text-red-400 p-8 text-center">{error}</div>}
          {!loading && !error && graphData && graphData.nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-center p-8">
              No knowledge graph entries yet.<br />Run <code className="bg-slate-800 px-1 rounded">graphiti add</code> or <code className="bg-slate-800 px-1 rounded">graphiti index</code> to populate.
            </div>
          )}
          {graphData && (
            <GraphCanvas
              data={graphData}
              search={search}
              typeFilter={typeFilter}
              colorMode={colorMode}
              layout={layout}
              onNodeClick={handleNodeClick}
            />
          )}
          <Legend colorMode={colorMode} nodes={graphData?.nodes ?? []} />
        </div>
        <NodeSidebar node={selectedNode} onClose={() => setSelectedNode(null)} />
      </div>
    </div>
  );
}
