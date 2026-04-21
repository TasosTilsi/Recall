import { useEffect, useRef } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import circular from 'graphology-layout/circular';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import type { GraphNode, GraphEdge } from '@/types/api';
import { ENTITY_TYPE_COLORS } from '@/lib/colors';

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedTypes?: string[];   // entity types to show; empty = show all
  searchQuery?: string;
  onNodeClick?: (nodeData: { id: string; label: string; type: string }) => void;
  onEdgeClick?: (edgeData: { id: string; source: string; target: string; relationship: string }) => void;
  onRendererReady?: (renderer: Sigma) => void;
}

const ENTITY_SIZE_MAX = 20;
const ENTITY_SIZE_MIN = 6;

export function GraphCanvas({
  nodes,
  edges,
  selectedTypes = [],
  searchQuery = '',
  onNodeClick,
  onEdgeClick,
  onRendererReady,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (nodes.length === 0) return;

    // Apply entity-type filter (empty selectedTypes = show all)
    const visibleNodes = selectedTypes.length > 0
      ? nodes.filter(n => selectedTypes.includes(n.type))
      : nodes;

    const graph = new Graph({ multi: false, allowSelfLoops: false });

    // Calculate backlink counts for node size scaling
    const backlinkCount: Record<string, number> = {};
    edges.forEach(e => {
      backlinkCount[e.from_id] = (backlinkCount[e.from_id] ?? 0) + 1;
      backlinkCount[e.to_id] = (backlinkCount[e.to_id] ?? 0) + 1;
    });
    const maxCount = Math.max(...Object.values(backlinkCount), 1);

    visibleNodes.forEach(n => {
      const count = backlinkCount[n.id] ?? 0;
      const size = ENTITY_SIZE_MIN + (count / maxCount) * (ENTITY_SIZE_MAX - ENTITY_SIZE_MIN);
      const color = ENTITY_TYPE_COLORS[n.type] ?? '#888888';
      const dim = searchQuery ? !n.label.toLowerCase().includes(searchQuery.toLowerCase()) : false;
      graph.addNode(n.id, {
        label: n.label,
        x: Math.random(),
        y: Math.random(),
        size: Math.max(ENTITY_SIZE_MIN, Math.min(ENTITY_SIZE_MAX, size)),
        color: dim ? color + '33' : color,
        type: 'circle',
      });
    });

    // Add edges (only between visible nodes)
    edges.forEach(e => {
      if (graph.hasNode(e.from_id) && graph.hasNode(e.to_id)) {
        try {
          graph.addEdge(e.from_id, e.to_id, {
            label: e.relationship,
            size: 1.5,
            color: '#64748b',
          });
        } catch {
          // Skip duplicate edges (multi=false)
        }
      }
    });

    circular.assign(graph);

    const renderer = new Sigma(graph, containerRef.current, {
      renderLabels: true,
      defaultEdgeColor: '#64748b',
      labelFont: 'Inter, ui-sans-serif, system-ui',
      labelSize: 11,
      labelColor: { color: '#94a3b8' },
      defaultNodeColor: '#888888',
    });

    onRendererReady?.(renderer);

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
        relationship: (attrs['label'] as string) ?? '',
      });
    });

    const fa2Timer = setTimeout(() => {
      try {
        const fa2Settings = forceAtlas2.inferSettings(graph);
        forceAtlas2.assign(graph, { iterations: 100, settings: fa2Settings });
        renderer.refresh();
      } catch {
        // FA2 failure is non-fatal
      }
    }, 100);

    return () => {
      clearTimeout(fa2Timer);
      renderer.kill();
    };
  }, [nodes, edges, selectedTypes, searchQuery, onNodeClick, onEdgeClick, onRendererReady]);

  if (nodes.length === 0) {
    return (
      <div
        className="w-full h-full flex items-center justify-center"
        style={{ backgroundColor: '#0b1326' }}
      >
        <div className="text-center">
          <h2 className="text-base font-semibold text-white mb-2">Graph is empty.</h2>
          <p className="text-slate-400 text-sm">
            Index your git history with <code className="text-blue-400">recall index</code>.
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
