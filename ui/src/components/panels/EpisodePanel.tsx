import { Badge } from '@/components/ui/badge';
import type { DetailEpisode } from '@/types/api';
import type { PanelItem } from './DetailPanel';
import { SOURCE_COLORS, ENTITY_TYPE_COLORS } from '@/lib/colors';
import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface EpisodePanelProps {
  episode: DetailEpisode;
  onNavigate: (item: PanelItem) => void;
}

export function EpisodePanel({ episode, onNavigate }: EpisodePanelProps) {
  const [contentExpanded, setContentExpanded] = useState(false);
  const src = episode.source || 'cli-add';
  const srcColor = SOURCE_COLORS[src] ?? '#94a3b8';
  const isLongContent = (episode.content?.length ?? 0) > 500;

  return (
    <div className="space-y-6">
      {/* Source + timestamps */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Badge className="text-[10px] h-4 uppercase tracking-widest px-1.5" style={{ backgroundColor: `${srcColor}22`, color: srcColor, border: 'none' }}>
            {src}
          </Badge>
          <span className="text-[10px] text-slate-500 uppercase tracking-tighter">{episode.created_at?.slice(0, 10) ?? '—'}</span>
        </div>
        <h2 className="text-xl font-semibold text-white tracking-tight leading-snug">{episode.source_description || episode.name}</h2>
      </div>

      {/* Content */}
      {episode.content && (
        <div className="bg-[#171f33] p-4 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Source Content</h3>
            {isLongContent && (
              <button
                className="text-[10px] text-slate-500 hover:text-slate-300 flex items-center gap-1 uppercase font-bold"
                onClick={() => setContentExpanded(!contentExpanded)}
              >
                {contentExpanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                {contentExpanded ? 'Collapse' : 'Expand'}
              </button>
            )}
          </div>
          <pre
            className="text-xs text-slate-300 overflow-auto whitespace-pre-wrap"
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
              lineHeight: 1.7,
              maxHeight: contentExpanded ? 'none' : '180px',
              overflow: contentExpanded ? 'visible' : 'hidden',
            }}
          >
            {episode.content}
          </pre>
        </div>
      )}

      {/* Entities */}
      {episode.entities && episode.entities.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Entities Extracted</h3>
          <ul className="grid gap-1">
            {episode.entities.map((ent) => (
              <li
                key={ent.uuid}
                className="flex items-center justify-between gap-2 px-3 py-2 rounded hover:bg-[#171f33] transition-colors cursor-pointer"
                onClick={() => onNavigate({ itemType: 'entity', itemId: ent.uuid, label: ent.name })}
              >
                <span className="text-sm font-medium text-blue-400/90 hover:text-blue-400">{ent.name}</span>
                {ent.tags?.[0] && (
                  <Badge className="text-[10px] h-4 uppercase tracking-widest px-1.5" style={{
                    backgroundColor: `${ENTITY_TYPE_COLORS[ent.tags[0]] ?? '#94a3b8'}15`,
                    color: ENTITY_TYPE_COLORS[ent.tags[0]] ?? '#94a3b8',
                    border: 'none',
                  }}>
                    {ent.tags[0]}
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
