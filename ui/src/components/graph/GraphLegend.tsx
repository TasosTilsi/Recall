import { ENTITY_TYPE_COLORS } from '@/lib/colors';

export function GraphLegend() {
  return (
    <div className="absolute bottom-4 left-4 z-10">
      <div
        className="p-3 rounded-lg flex flex-col gap-1.5"
        style={{ backgroundColor: 'rgba(34,42,61,0.88)', backdropFilter: 'blur(12px)' }}
      >
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Entity Types</span>
        {Object.entries(ENTITY_TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
            <span className="text-xs text-slate-300">{type.replace('_', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
