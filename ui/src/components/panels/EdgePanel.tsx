import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import type { DetailEdge } from '@/types/api';
import type { PanelItem } from './DetailPanel';

interface EdgePanelProps {
  edge: DetailEdge;
  onNavigate: (item: PanelItem) => void;
}

export function EdgePanel({ edge, onNavigate }: EdgePanelProps) {
  return (
    <div className="space-y-4">
      {/* Fact — prominent at top */}
      <div>
        <h2 className="text-base font-semibold text-white leading-relaxed">{edge.fact || 'No fact recorded'}</h2>
        <Badge className="text-xs mt-2" style={{ backgroundColor: '#1e293b', color: '#94a3b8', border: '1px solid #475569' }}>
          {edge.label || 'RELATES_TO'}
        </Badge>
      </div>

      <Separator style={{ backgroundColor: '#334155' }} />

      {/* Source → Target */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-slate-400 text-xs w-12">From</span>
          <button
            className="text-blue-400 hover:text-blue-300 text-sm truncate text-left"
            onClick={() => onNavigate({ itemType: 'entity', itemId: edge.source, label: edge.source })}
          >
            {edge.source}
          </button>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-slate-400 text-xs w-12">To</span>
          <button
            className="text-blue-400 hover:text-blue-300 text-sm truncate text-left"
            onClick={() => onNavigate({ itemType: 'entity', itemId: edge.target, label: edge.target })}
          >
            {edge.target}
          </button>
        </div>
      </div>
    </div>
  );
}
