import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchDashboard } from '@/api/client';
import type { RecentCommit } from '@/types/api';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

// Episodes route replaced with Recent Commits view (v3.0 — no episode concept)
export default function Episodes() {
  const { setLastUpdated } = useAppContext();
  const [commits, setCommits] = useState<RecentCommit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchDashboard();
        if (!cancelled) {
          setCommits(data.recent_commits);
          setLastUpdated(new Date());
          setLoading(false);
        }
      } catch { if (!cancelled) { setError("Could not reach API — is `recall ui` running?"); setLoading(false); } }
    };
    load();
    const iv = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [setLastUpdated]);

  if (loading) return (
    <div className="flex-1 p-6" style={{ backgroundColor: '#0f172a' }}>
      {[0, 1, 2].map(i => <Skeleton key={i} className="h-28 rounded-lg bg-slate-800 mb-3" />)}
    </div>
  );

  if (error) return (
    <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: '#0f172a' }}>
      <p className="text-red-400 text-sm">{error}</p>
    </div>
  );

  if (commits.length === 0) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ backgroundColor: '#0f172a' }}>
      <h2 className="text-base font-semibold text-white">No commits indexed yet.</h2>
      <p className="text-slate-400 text-sm">Run <code className="text-blue-400">recall index</code> to index git history.</p>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#0f172a' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b flex-shrink-0" style={{ borderColor: '#334155' }}>
        <span className="text-sm font-semibold text-white">Recent Commits</span>
        <span className="text-xs text-slate-400 ml-auto">{commits.length} commits</span>
      </div>

      {/* Commit cards */}
      <div className="flex-1 overflow-auto p-4 space-y-3">
        {commits.map(commit => (
          <Card
            key={commit.sha}
            className="p-4 transition-colors"
            style={{ backgroundColor: '#1e293b', borderColor: '#334155' }}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-200 font-medium truncate">{commit.message}</p>
                <p className="text-xs text-slate-500 mt-0.5">{commit.author} · {commit.date?.slice(0, 10) ?? ''}</p>
              </div>
              <code className="text-[10px] text-blue-400 font-mono flex-shrink-0 bg-[#131b2e] px-2 py-1 rounded">
                {commit.sha.slice(0, 8)}
              </code>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
