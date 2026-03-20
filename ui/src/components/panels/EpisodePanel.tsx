import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
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
    <div className="space-y-4">
      {/* Source + timestamps */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Badge style={{ backgroundColor: `${srcColor}22`, color: srcColor, border: `1px solid ${srcColor}44` }}>
            {src}
          </Badge>
        </div>
        <h2 className="text-sm font-medium text-white">{episode.source_description || episode.name}</h2>
        <p className="text-xs text-slate-400 mt-1">{episode.created_at?.slice(0, 16) ?? '—'}</p>
      </div>

      {/* Content */}
      {episode.content && (
        <>
          <Separator style={{ backgroundColor: '#334155' }} />
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs text-slate-400">Content</h3>
              {isLongContent && (
                <button
                  className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1"
                  onClick={() => setContentExpanded(!contentExpanded)}
                >
                  {contentExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  {contentExpanded ? 'Collapse' : 'Expand'}
                </button>
              )}
            </div>
            <pre
              className="text-xs text-slate-300 bg-slate-900 p-3 rounded overflow-auto whitespace-pre-wrap"
              style={{
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                lineHeight: 1.6,
                maxHeight: contentExpanded ? 'none' : '200px',
                overflow: contentExpanded ? 'visible' : 'hidden',
              }}
            >
              {episode.content}
            </pre>
          </div>
        </>
      )}

      {/* Entities */}
      {episode.entities && episode.entities.length > 0 && (
        <>
          <Separator style={{ backgroundColor: '#334155' }} />
          <div>
            <h3 className="text-xs text-slate-400 mb-2">Entities Extracted ({episode.entities.length})</h3>
            <ul className="space-y-1.5">
              {episode.entities.map((ent) => (
                <li
                  key={ent.uuid}
                  className="flex items-center gap-2 text-sm cursor-pointer hover:bg-slate-700/50 p-1.5 rounded"
                  onClick={() => onNavigate({ itemType: 'entity', itemId: ent.uuid, label: ent.name })}
                >
                  <span className="text-blue-400 hover:text-blue-300">{ent.name}</span>
                  {ent.tags?.[0] && (
                    <Badge className="text-xs" style={{
                      backgroundColor: `${ENTITY_TYPE_COLORS[ent.tags[0]] ?? '#94a3b8'}22`,
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
        </>
      )}
    </div>
  );
}
