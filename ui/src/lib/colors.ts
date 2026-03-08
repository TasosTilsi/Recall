// Dark-mode optimized palette for entity types
const TYPE_COLORS: Record<string, string> = {
  'Decision':     '#60a5fa',  // blue-400
  'Architecture': '#a78bfa',  // violet-400
  'Bug Fix':      '#f87171',  // red-400
  'Dependency':   '#34d399',  // emerald-400
  'Pattern':      '#fbbf24',  // amber-400
  'Preference':   '#f472b6',  // pink-400
  'Entity':       '#94a3b8',  // slate-400 (default)
};

const SCOPE_COLORS: Record<string, string> = {
  project: '#60a5fa',  // blue-400
  global:  '#a78bfa',  // violet-400
};

export function getNodeColor(node: { entityType?: string; scope?: string }, mode: 'type' | 'scope'): string {
  if (mode === 'scope') {
    return SCOPE_COLORS[node.scope ?? 'project'] ?? '#94a3b8';
  }
  return TYPE_COLORS[node.entityType ?? 'Entity'] ?? '#94a3b8';
}

export function getLegendEntries(mode: 'type' | 'scope'): { label: string; color: string }[] {
  if (mode === 'scope') {
    return Object.entries(SCOPE_COLORS).map(([label, color]) => ({ label, color }));
  }
  return Object.entries(TYPE_COLORS).map(([label, color]) => ({ label, color }));
}
