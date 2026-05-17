// Recall Obsidian palette — six canonical entity types only
export const ENTITY_TYPE_COLORS: Record<string, string> = {
  decision:  '#00d4ff',  // cyan
  bug_fix:   '#ff4d4d',  // red
  pattern:   '#a78bfa',  // purple
  file:      '#6ee7b7',  // mint
  concept:   '#fbbf24',  // amber
  tech_debt: '#f97316',  // orange
  workflow:  '#ec4899',  // pink
  business_rule: '#10b981', // emerald
};

export function getEntityColor(type: string): string {
  return ENTITY_TYPE_COLORS[type] ?? '#888888';
}
