import { ENTITY_TYPE_COLORS, SCOPE_COLORS, RETENTION_COLORS } from '@/lib/colors';

interface GraphLegendProps {
  colorMode: 'type' | 'scope';
}

const RETENTION_RING_ENTRIES = [
  { name: 'Pinned', color: RETENTION_COLORS.Pinned },
  { name: 'Stale', color: RETENTION_COLORS.Stale },
  { name: 'Archived', color: RETENTION_COLORS.Archived },
  { name: 'Normal', color: '#334155' },  // slate-700: "no ring"
];

export function GraphLegend({ colorMode }: GraphLegendProps) {
  const entries = colorMode === 'scope'
    ? Object.entries(SCOPE_COLORS).map(([name, color]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        color,
      }))
    : Object.entries(ENTITY_TYPE_COLORS).map(([name, color]) => ({ name, color }));

  return (
    <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-3">
      {/* Entity type / scope legend */}
      <div
        className="p-3 rounded-lg flex flex-col gap-1.5"
        style={{ backgroundColor: 'rgba(34,42,61,0.88)', backdropFilter: 'blur(12px)' }}
      >
        {entries.map(({ name, color }) => (
          <div key={name} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
            <span className="text-xs text-slate-300">{name}</span>
          </div>
        ))}
      </div>

      {/* Retention ring legend */}
      <div
        className="p-3 rounded-lg flex flex-col gap-1.5"
        style={{ backgroundColor: 'rgba(34,42,61,0.88)', backdropFilter: 'blur(12px)' }}
      >
        <span className="text-xs text-slate-400 font-medium mb-0.5">Retention</span>
        {RETENTION_RING_ENTRIES.map(({ name, color }) => (
          <div key={name} className="flex items-center gap-2">
            <div
              className="w-2.5 h-2.5 rounded-full flex-shrink-0 border-2"
              style={{ borderColor: color, backgroundColor: 'transparent' }}
            />
            <span className="text-xs text-slate-300">{name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
