'use client';
import ForceGraph2D from 'react-force-graph-2d';
import { useRef, useCallback } from 'react';
import { GraphData, NodeData } from '@/lib/api';
import { getNodeColor } from '@/lib/colors';

interface Props {
  data: GraphData;
  search: string;
  typeFilter: string;
  colorMode: 'type' | 'scope';
  layout: 'hierarchical' | 'force';
  onNodeClick: (node: NodeData) => void;
}

export function GraphCanvas({ data, search, typeFilter, colorMode, layout, onNodeClick }: Props) {
  const graphRef = useRef<any>(null);

  const nodeColor = useCallback((node: any) => {
    // Dim non-matching nodes when search/filter active
    const matchesSearch = !search || node.name.toLowerCase().includes(search.toLowerCase());
    const matchesType = !typeFilter || node.entityType === typeFilter;
    if (!matchesSearch || !matchesType) return '#1e293b';  // dim — slate-800
    return getNodeColor(node, colorMode);
  }, [search, typeFilter, colorMode]);

  return (
    <ForceGraph2D
      ref={graphRef}
      graphData={data as any}
      dagMode={layout === 'hierarchical' ? 'td' : undefined}
      dagLevelDistance={60}
      nodeColor={nodeColor}
      nodeLabel="name"
      onNodeClick={(node: any) => onNodeClick(node as NodeData)}
      backgroundColor="#0f172a"
      linkColor={() => '#334155'}
      nodeCanvasObjectMode={() => 'after'}
      nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        if (globalScale < 1.2) return;
        ctx.font = `${12 / globalScale}px sans-serif`;
        ctx.fillStyle = '#f1f5f9';
        ctx.textAlign = 'center';
        ctx.fillText(node.name, node.x, node.y + (node.val ?? 5) + 3);
      }}
    />
  );
}
