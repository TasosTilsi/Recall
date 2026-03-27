export const ENTITY_TYPE_COLORS: Record<string, string> = {
  Decision: '#60a5fa',       // blue-400
  Architecture: '#a78bfa',   // violet-400
  'Bug Fix': '#f87171',      // red-400
  Dependency: '#34d399',     // emerald-400
  Pattern: '#fbbf24',        // amber-400
  Preference: '#f472b6',     // pink-400
  Entity: '#94a3b8',         // slate-400 (default)
};

export const SCOPE_COLORS: Record<string, string> = {
  project: '#60a5fa',   // blue-400
  global: '#a78bfa',    // violet-400
};

export const RETENTION_COLORS: Record<string, string> = {
  Pinned: '#fbbf24',     // amber-400
  Normal: '#4ade80',     // green-400
  Stale: '#f87171',      // red-400
  Archived: '#94a3b8',   // slate-400
};

export const SOURCE_COLORS: Record<string, string> = {
  'git-index': '#60a5fa',      // blue-400
  'hook-capture': '#a78bfa',   // violet-400
  'cli-add': '#34d399',        // emerald-400
};

export function getEntityColor(type: string): string {
  return ENTITY_TYPE_COLORS[type] ?? ENTITY_TYPE_COLORS['Entity'];
}

export function getRetentionBorderColor(status: string | undefined): string | undefined {
  if (!status || status === 'Normal') return undefined;
  return RETENTION_COLORS[status];
}
