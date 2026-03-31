import { Badge } from '@/components/ui/badge';
import type { DetailEdge } from '@/types/api';
import type { PanelItem } from './DetailPanel';

interface EdgePanelProps {
  edge: DetailEdge;
  onNavigate: (item: PanelItem) => void;
}

export function EdgePanel({ edge, onNavigate }: EdgePanelProps) {
  return (
    <div className="space-y-6">
      {/* Fact — prominent at top */}
      <div>
        <h2 className="text-lg font-medium text-white leading-relaxed tracking-tight">{edge.fact || 'No fact recorded'}</h2>
        <Badge className="text-[10px] h-4 uppercase tracking-widest px-1.5 mt-3" style={{ backgroundColor: '#171f33', color: '#94a3b8', border: 'none' }}>
          {edge.label || 'RELATES_TO'}
        </Badge>
      </div>

      {/* Source → Target */}
      <div className="space-y-4 bg-[#171f33] p-4 rounded-lg">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Source</span>
          <button
            className="text-blue-400 hover:text-blue-300 text-sm font-medium text-left truncate"
            onClick={() => onNavigate({ itemType: 'entity', itemId: edge.source, label: edge.source })}
          >
            {edge.source}
          </button>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Target</span>
          <button
            className="text-blue-400 hover:text-blue-300 text-sm font-medium text-left truncate"
            onClick={() => onNavigate({ itemType: 'entity', itemId: edge.target, label: edge.target })}
          >
            {edge.target}
          </button>
        </div>
      </div>
    </div>
  );
}
