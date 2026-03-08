'use client';
import { NodeDetail } from '@/lib/api';

interface Props {
  node: NodeDetail | null;
  onClose: () => void;
}

export default function NodeSidebar({ node, onClose }: Props) {
  if (!node) return null;
  return (
    <aside className="w-80 bg-slate-900 border-l border-slate-800 overflow-y-auto p-4 flex flex-col gap-3 text-sm">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-bold text-white text-base">{node.name}</div>
          <div className="text-xs text-blue-400">{node.entityType}</div>
        </div>
        <button onClick={onClose} className="text-slate-500 hover:text-white ml-2">&#x2715;</button>
      </div>
      {node.summary && <p className="text-slate-300 text-xs leading-relaxed">{node.summary}</p>}
      <div className="flex gap-3 text-xs text-slate-400">
        <span>{node.pinned ? 'Pinned' : 'Not pinned'}</span>
        <span>Access: {node.accessCount}</span>
      </div>
      <div className="text-xs text-slate-500">
        <div>Created: {node.createdAt ? new Date(node.createdAt).toLocaleDateString() : '—'}</div>
        <div>Last accessed: {node.lastAccessedAt ? new Date(node.lastAccessedAt).toLocaleDateString() : '—'}</div>
      </div>
      {node.relationships?.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-400 mb-1">Relationships</div>
          <ul className="space-y-1">
            {node.relationships.map((r, i) => (
              <li key={i} className="text-xs text-slate-300">
                <span className="text-slate-500">{r.label}</span> {r.name || r.target}
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
