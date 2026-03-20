interface StatusBarProps {
  entities: number;
  edges: number;
  episodes: number;
}

export function StatusBar({ entities, edges, episodes }: StatusBarProps) {
  return (
    <footer
      className="flex items-center justify-center text-xs text-slate-400 flex-shrink-0"
      style={{ height: '32px', backgroundColor: '#1e293b', borderTop: '1px solid #334155' }}
    >
      {entities.toLocaleString()} entities · {edges.toLocaleString()} edges · {episodes.toLocaleString()} episodes
    </footer>
  );
}
