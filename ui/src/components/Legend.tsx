'use client';
import { NodeData } from '@/lib/api';
import { getLegendEntries } from '@/lib/colors';

interface Props {
  colorMode: 'type' | 'scope';
  nodes: NodeData[];
}

export default function Legend({ colorMode, nodes }: Props) {
  // Only show entity types that are actually present in the graph
  const activeTypes = new Set(nodes.map(n => n.entityType));
  const entries = getLegendEntries(colorMode).filter(e =>
    colorMode === 'scope' || activeTypes.has(e.label)
  );
  if (entries.length === 0) return null;
  return (
    <div className="absolute bottom-4 left-4 bg-slate-900/80 border border-slate-800 rounded p-2 text-xs space-y-1">
      {entries.map(({ label, color }) => (
        <div key={label} className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
          <span className="text-slate-300">{label}</span>
        </div>
      ))}
    </div>
  );
}
