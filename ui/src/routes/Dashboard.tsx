import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchDashboard } from '@/api/client';
import type { DashboardData } from '@/types/api';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { ENTITY_TYPE_COLORS } from '@/lib/colors';

// --- Stat Card component ---
function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card
      className="p-5 flex flex-col gap-1 cursor-pointer hover:bg-[#2d3449] transition-colors"
      style={{ backgroundColor: '#222a3d', border: 'none' }}
    >
      <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
      <span className="text-3xl font-semibold text-white tracking-tight">{value.toLocaleString()}</span>
    </Card>
  );
}

// --- Main Dashboard component ---
export default function Dashboard() {
  const { setLastUpdated } = useAppContext();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await fetchDashboard();
        if (!cancelled) {
          setData(result);
          setLastUpdated(new Date());
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError("Could not reach API — is `recall ui` running?");
          setLoading(false);
        }
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30_000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [setLastUpdated]);

  if (loading) {
    return (
      <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0b1326' }}>
        <div className="grid grid-cols-2 gap-4 mb-6">
          {[0, 1].map(i => <Skeleton key={i} className="h-24 rounded-lg bg-slate-800" />)}
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          {[0, 1].map(i => <Skeleton key={i} className="h-48 rounded-lg bg-slate-800" />)}
        </div>
        <Skeleton className="h-48 rounded-lg bg-slate-800" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: '#0b1326' }}>
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  if (!data || data.total_entities === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ backgroundColor: '#0b1326' }}>
        <h2 className="text-base font-semibold text-white">No knowledge yet.</h2>
        <p className="text-slate-400 text-sm">Run <code className="text-blue-400">recall index</code> to populate.</p>
      </div>
    );
  }

  // Entity type donut data
  const entityTypeData = Object.entries(data.entity_types).map(([name, value]) => ({
    name, value, color: ENTITY_TYPE_COLORS[name] ?? '#888888',
  }));

  return (
    <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0b1326' }}>
      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <StatCard label="Entities" value={data.total_entities} />
        <StatCard label="Commits Indexed" value={data.total_commits} />
      </div>

      {/* Charts row: Entity Types + Top Entities */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Entity Type Distribution donut */}
        <Card className="p-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
          <h2 className="text-sm font-semibold text-white mb-3">Entity Types</h2>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={entityTypeData} cx="50%" cy="50%" innerRadius={45} outerRadius={65} dataKey="value">
                {entityTypeData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#222a3d', border: 'none', color: '#e2e8f0' }} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Top Connected Entities horizontal bar */}
        <Card className="p-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
          <h2 className="text-sm font-semibold text-white mb-3">Top Entities</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={data.top_entities} layout="vertical">
              <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis type="category" dataKey="name" width={90} stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <Tooltip contentStyle={{ backgroundColor: '#222a3d', border: 'none', color: '#e2e8f0' }} />
              <Bar dataKey="backlink_count" name="Backlinks" fill="#60a5fa" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Recent Commits */}
      <Card className="p-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
        <h2 className="text-sm font-semibold text-white mb-3">Recent Commits</h2>
        {data.recent_commits.length === 0 ? (
          <p className="text-slate-500 text-sm">No recent commits.</p>
        ) : (
          <ul className="space-y-1">
            {data.recent_commits.map((commit) => (
              <li
                key={commit.sha}
                className="flex items-start gap-4 px-3 py-3 rounded-md transition-colors hover:bg-[#171f33]"
              >
                <code className="text-[10px] text-blue-400 font-mono mt-0.5 flex-shrink-0 w-16 truncate">{commit.sha}</code>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{commit.message}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{commit.author} · {commit.date?.slice(0, 10) ?? ''}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
