import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { DetailEntity } from '@/types/api';
import type { PanelItem } from './DetailPanel';
import { ENTITY_TYPE_COLORS, RETENTION_COLORS } from '@/lib/colors';

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
    <div className="space-y-4">
      {/* Name + type badge */}
      <div>
        <h2 className="text-base font-semibold text-white">{entity.name}</h2>
        <div className="flex items-center gap-2 mt-1">
          <Badge className="text-xs" style={{
            backgroundColor: `${ENTITY_TYPE_COLORS[type] ?? '#94a3b8'}22`,
            color: ENTITY_TYPE_COLORS[type] ?? '#94a3b8',
            border: `1px solid ${ENTITY_TYPE_COLORS[type] ?? '#94a3b8'}44`,
          }}>
            {type}
          </Badge>
          <Badge className="text-xs" style={{
            backgroundColor: `${RETENTION_COLORS[status] ?? '#94a3b8'}22`,
            color: RETENTION_COLORS[status] ?? '#94a3b8',
            border: `1px solid ${RETENTION_COLORS[status] ?? '#94a3b8'}44`,
          }}>
            {status}
          </Badge>
        </div>
      </div>

      {/* Summary */}
      {entity.summary && (
        <>
          <Separator style={{ backgroundColor: '#334155' }} />
          <div>
            <h3 className="text-xs text-slate-400 mb-1">Summary</h3>
            <p className="text-sm text-slate-300 leading-relaxed">{entity.summary}</p>
          </div>
        </>
      )}

      {/* Metadata */}
      <Separator style={{ backgroundColor: '#334155' }} />
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="text-slate-400">Created</span>
          <span className="text-slate-300">{entity.created_at?.slice(0, 16) ?? '—'}</span>
        </div>
        {entity.access_count !== undefined && (
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Access count</span>
            <span className="text-slate-300">{entity.access_count}</span>
          </div>
        )}
      </div>

      {/* Relationships */}
      {entity.relationships && entity.relationships.length > 0 && (
        <>
          <Separator style={{ backgroundColor: '#334155' }} />
          <div>
            <h3 className="text-xs text-slate-400 mb-2">Relationships ({entity.relationships.length})</h3>
            <ul className="space-y-1.5">
              {entity.relationships.slice(0, 20).map((rel, i) => (
                <li
                  key={i}
                  className="text-xs text-slate-300 p-2 rounded cursor-pointer hover:bg-slate-700/50"
                  onClick={() => onNavigate({ itemType: 'edge', itemId: `${rel.source}-${rel.target}`, label: rel.label || rel.fact?.slice(0, 40) || 'Edge' })}
                >
                  <span className="text-slate-400">{rel.label || 'RELATES_TO'}</span>
                  {rel.fact && <p className="text-slate-500 mt-0.5 truncate">{rel.fact}</p>}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
