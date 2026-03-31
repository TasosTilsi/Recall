import { useEffect, useRef } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import circular from 'graphology-layout/circular';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import type { GraphNode, GraphEdge } from '@/types/api';
import { getEntityColor, getRetentionBorderColor } from '@/lib/colors';

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  showEpisodes?: boolean;
  searchQuery?: string;
  colorMode?: 'type' | 'scope';
  onNodeClick?: (nodeData: { id: string; label: string; type: string }) => void;
  onEdgeClick?: (edgeData: { id: string; source: string; target: string; name: string }) => void;
  onRendererReady?: (renderer: Sigma) => void;
}

const EPISODE_COLOR = '#475569';  // slate-600
const ENTITY_SIZE_MAX = 20;
const ENTITY_SIZE_MIN = 6;
const EPISODE_SIZE = 6;

export function GraphCanvas({
  nodes,
  edges,
  showEpisodes = false,
  searchQuery = '',
  colorMode = 'type',
  onNodeClick,
  onEdgeClick,
  onRendererReady,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (nodes.length === 0) return;

    // Build graphology graph
    const graph = new Graph({ multi: false, allowSelfLoops: false });

    // Calculate edge counts per node for size scaling
    const edgeCount: Record<string, number> = {};
    edges.forEach(e => {
      edgeCount[e.source] = (edgeCount[e.source] ?? 0) + 1;
      edgeCount[e.target] = (edgeCount[e.target] ?? 0) + 1;
    });
    const maxEdges = Math.max(...Object.values(edgeCount), 1);

    // Separate entity nodes from episode nodes
    const entityNodes = nodes.filter(n => n.type !== 'Episodic');
    const episodeNodes = nodes.filter(n => n.type === 'Episodic');

    // Add entity nodes
    entityNodes.forEach(n => {
      const count = edgeCount[n.id] ?? 0;
      const size = ENTITY_SIZE_MIN + (count / maxEdges) * (ENTITY_SIZE_MAX - ENTITY_SIZE_MIN);
      const color = colorMode === 'scope'
        ? (n.scope === 'global' ? '#a78bfa' : '#60a5fa')
        : getEntityColor(n.type);
      const dim = searchQuery ? !n.label.toLowerCase().includes(searchQuery.toLowerCase()) : false;
      graph.addNode(n.id, {
        label: n.label,
        x: Math.random(),
        y: Math.random(),
        size: Math.max(ENTITY_SIZE_MIN, Math.min(ENTITY_SIZE_MAX, size)),
        color: dim ? color + '33' : color,
        type: 'circle',
        borderColor: getRetentionBorderColor(n.retention_status),
        borderSize: n.retention_status && n.retention_status !== 'Normal' ? 4 : 0,
      });
    });

    // Add episode nodes if toggled on
    if (showEpisodes) {
      episodeNodes.forEach(n => {
        if (!graph.hasNode(n.id)) {
          graph.addNode(n.id, {
            label: n.label,
            x: Math.random(),
            y: Math.random(),
            size: EPISODE_SIZE,
            color: EPISODE_COLOR,
            type: 'square',  // diamond via @sigma/node-square (rotated 45deg in WebGL)
          });
        }
      });
    }

    // Add edges (only between nodes that exist in graph)
    edges.forEach(e => {
      if (graph.hasNode(e.source) && graph.hasNode(e.target)) {
        try {
          const isEpisodeEdge = episodeNodes.some(n => n.id === e.source || n.id === e.target);
          graph.addEdge(e.source, e.target, {
            label: e.name,
            size: isEpisodeEdge ? 1 : 1.5,
            color: isEpisodeEdge ? '#475569' : '#64748b',
          });
        } catch {
          // Skip duplicate edges (multi=false)
        }
      }
    });

    // Deterministic circular layout
    circular.assign(graph);

    // Sigma WebGL renderer
    const renderer = new Sigma(graph, containerRef.current, {
      renderLabels: true,
      defaultEdgeColor: '#64748b',
      labelFont: 'Inter, ui-sans-serif, system-ui',
      labelSize: 11,
      labelColor: { color: '#94a3b8' },
      defaultNodeColor: '#94a3b8',
    });

    onRendererReady?.(renderer);

    // Click handlers
    renderer.on('clickNode', ({ node }) => {
      const attrs = graph.getNodeAttributes(node);
      onNodeClick?.({ id: node, label: (attrs['label'] as string) ?? '', type: (attrs['type'] as string) ?? '' });
    });

    renderer.on('clickEdge', ({ edge }) => {
      const attrs = graph.getEdgeAttributes(edge);
      onEdgeClick?.({
        id: edge,
        source: graph.source(edge),
        target: graph.target(edge),
        name: (attrs['label'] as string) ?? '',
      });
    });

    // FA2 physics after initial render (non-blocking via setTimeout)
    const fa2Timer = setTimeout(() => {
      try {
        const fa2Settings = forceAtlas2.inferSettings(graph);
        forceAtlas2.assign(graph, { iterations: 100, settings: fa2Settings });
        renderer.refresh();
      } catch {
        // FA2 failure is non-fatal — circular layout still visible
      }
    }, 100);

    return () => {
      clearTimeout(fa2Timer);
      renderer.kill();
    };
  }, [nodes, edges, showEpisodes, searchQuery, colorMode, onNodeClick, onEdgeClick, onRendererReady]);

  if (nodes.length === 0) {
    return (
      <div
        className="w-full h-full flex items-center justify-center"
        style={{ backgroundColor: '#0b1326' }}
      >
        <div className="text-center">
          <h2 className="text-base font-semibold text-white mb-2">Graph is empty.</h2>
          <p className="text-slate-400 text-sm">
            Add episodes with <code className="text-blue-400">recall add</code> or index your git history with{' '}
            <code className="text-blue-400">recall index</code>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-full graph-dot-grid"
      style={{ backgroundColor: '#0b1326' }}
    />
  );
}
