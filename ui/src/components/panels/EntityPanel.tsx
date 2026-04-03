import { Badge } from '@/components/ui/badge';
import type { DetailEntity } from '@/types/api';
import type { PanelItem } from './DetailPanel';
import { ENTITY_TYPE_COLORS, RETENTION_COLORS } from '@/lib/colors';
import { parseCodeBlockMeta } from '@/lib/parseCodeBlockMeta';

interface EntityPanelProps {
  entity: DetailEntity;
  onNavigate: (item: PanelItem) => void;
}

function retentionStatus(entity: DetailEntity): string {
  if (entity.pinned) return 'Pinned';
  return 'Normal';
}

export function EntityPanel({ entity, onNavigate }: EntityPanelProps) {
  const type = entity.tags?.[0] ?? 'Entity';
  const status = retentionStatus(entity);

  return (
    <div className="space-y-6">
      {/* Name + type badge */}
      <div>
        <h2 className="text-xl font-semibold text-white tracking-tight leading-none mb-2">{entity.name}</h2>
        <div className="flex items-center gap-1.5 mt-2">
          <Badge className="text-[10px] h-4 uppercase tracking-widest px-1.5" style={{
            backgroundColor: `${ENTITY_TYPE_COLORS[type] ?? '#94a3b8'}22`,
            color: ENTITY_TYPE_COLORS[type] ?? '#94a3b8',
            border: 'none',
          }}>
            {type}
          </Badge>
          <Badge className="text-[10px] h-4 uppercase tracking-widest px-1.5" style={{
            backgroundColor: `${RETENTION_COLORS[status] ?? '#94a3b8'}22`,
            color: RETENTION_COLORS[status] ?? '#94a3b8',
            border: 'none',
          }}>
            {status}
          </Badge>
        </div>

        {/* Code block metadata chips — per D-08, D-10 */}
        {(() => {
          const meta = entity.summary ? parseCodeBlockMeta(entity.summary) : null;
          if (!meta) return null;
          return (
            <div className="flex items-center gap-2 flex-wrap mt-2">
              <span className="text-xs text-slate-400 font-mono">
                {'\u{1F4C4}'} {meta.file}
              </span>
              {meta.language && (
                <Badge className="text-[10px] h-4 px-1.5" style={{
                  backgroundColor: '#22d3ee22',
                  color: '#22d3ee',
                  border: 'none',
                }}>
                  {meta.language}
                </Badge>
              )}
            </div>
          );
        })()}
      </div>

      {/* Summary */}
      {entity.summary && (
        <div className="bg-[#171f33] p-4 rounded-lg">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Summary</h3>
          <p className="text-sm text-slate-300 leading-relaxed">
            {(() => {
              const meta = entity.summary ? parseCodeBlockMeta(entity.summary) : null;
              return meta?.remainder || entity.summary;
            })()}
          </p>
        </div>
      )}

      {/* Relationships */}
      {entity.relationships && entity.relationships.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Relationships</h3>
          <ul className="grid gap-1">
            {entity.relationships.slice(0, 15).map((rel, i) => (
              <li
                key={i}
                className="group flex flex-col px-3 py-2.5 rounded hover:bg-[#171f33] transition-all cursor-pointer"
                onClick={() => onNavigate({ itemType: 'edge', itemId: `${rel.source}-${rel.target}`, label: rel.label || rel.fact?.slice(0, 40) || 'Edge' })}
              >
                <span className="text-[10px] font-medium text-blue-400/70 group-hover:text-blue-400 uppercase tracking-wider">{rel.label || 'RELATES_TO'}</span>
                <span className="text-xs text-slate-300 mt-1 line-clamp-2">{rel.fact || '...'}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
