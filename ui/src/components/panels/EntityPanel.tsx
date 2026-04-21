import { Badge } from '@/components/ui/badge';
import type { DetailEntityV3, Backlink } from '@/types/api';
import { ENTITY_TYPE_COLORS } from '@/lib/colors';

interface EntityPanelProps {
  entity: DetailEntityV3;
}

export function EntityPanel({ entity }: EntityPanelProps) {
  const typeColor = ENTITY_TYPE_COLORS[entity.type] ?? '#888888';

  return (
    <div className="space-y-6">
      {/* Name + type badge */}
      <div>
        <h2 className="text-xl font-semibold text-white tracking-tight leading-none mb-2">{entity.name}</h2>
        <div className="flex items-center gap-1.5 mt-2 flex-wrap">
          <Badge className="text-[10px] h-4 uppercase tracking-widest px-1.5" style={{
            backgroundColor: `${typeColor}22`,
            color: typeColor,
            border: 'none',
          }}>
            {entity.type.replace('_', ' ')}
          </Badge>
          {entity.tags.map(tag => (
            <Badge key={tag} className="text-[10px] h-4 px-1.5" style={{
              backgroundColor: '#1e2a4022',
              color: '#94a3b8',
              border: '1px solid #334155',
            }}>
              {tag}
            </Badge>
          ))}
        </div>
      </div>

      {/* Commit SHA */}
      {entity.commit_sha && (
        <div className="bg-[#171f33] px-4 py-3 rounded-lg">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Commit</h3>
          <code className="text-xs text-blue-400 font-mono">{entity.commit_sha}</code>
        </div>
      )}

      {/* Content */}
      {entity.content && (
        <div className="bg-[#171f33] p-4 rounded-lg">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Content</h3>
          <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{entity.content}</p>
        </div>
      )}

      {/* Backlinks */}
      {entity.backlinks && entity.backlinks.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            Backlinks ({entity.backlinks.length})
          </h3>
          <ul className="grid gap-1">
            {entity.backlinks.slice(0, 20).map((bl: Backlink, i: number) => (
              <li
                key={i}
                className="flex flex-col px-3 py-2.5 rounded bg-[#171f33]"
              >
                <span className="text-[10px] font-medium text-blue-400/70 uppercase tracking-wider">
                  {bl.relationship}
                </span>
                <span className="text-xs font-medium text-slate-200 mt-0.5">{bl.from_name}</span>
                {bl.context && (
                  <span className="text-xs text-slate-400 mt-1 line-clamp-2">{bl.context}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {entity.backlinks && entity.backlinks.length === 0 && (
        <p className="text-xs text-slate-500">No backlinks yet.</p>
      )}
    </div>
  );
}
