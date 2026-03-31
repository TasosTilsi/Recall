import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/AppContext';
import { fetchDashboard } from '@/api/client';
import type { DashboardData } from '@/types/api';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { ENTITY_TYPE_COLORS, RETENTION_COLORS, SOURCE_COLORS } from '@/lib/colors';

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

// --- Activity Heatmap (custom SVG, ~80 lines) ---
function ActivityHeatmap({ data }: { data: { day: string; count: number }[] }) {
  // Build 52-week grid from data
  const today = new Date();
  const weeks: { day: Date; count: number }[][] = [];
  let week: { day: Date; count: number }[] = [];
  const countByDay: Record<string, number> = {};
  data.forEach(({ day, count }) => { countByDay[day] = count; });

  for (let i = 364; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    week.push({ day: d, count: countByDay[key] ?? 0 });
    if (d.getDay() === 6) {
      weeks.push(week);
      week = [];
    }
  }
  if (week.length > 0) weeks.push(week);

  const maxCount = Math.max(...data.map(d => d.count), 1);
  const cellSize = 12;
  const gap = 2;
  const totalW = weeks.length * (cellSize + gap);
  const totalH = 7 * (cellSize + gap);

  const getColor = (count: number) => {
    if (count === 0) return '#1e293b';
    const intensity = Math.min(count / maxCount, 1);
    if (intensity < 0.25) return '#1e3a5f';
    if (intensity < 0.5) return '#1d4ed8';
    if (intensity < 0.75) return '#3b82f6';
    return '#93c5fd';
  };

  return (
    <div className="overflow-x-auto">
      <svg width={totalW} height={totalH + 20}>
        {weeks.map((week, wi) =>
          week.map(({ day, count }, di) => (
            <rect
              key={`${wi}-${di}`}
              x={wi * (cellSize + gap)}
              y={di * (cellSize + gap)}
              width={cellSize}
              height={cellSize}
              rx={2}
              fill={getColor(count)}
            >
              <title>{`${day.toISOString().slice(0, 10)}: ${count} episodes`}</title>
            </rect>
          ))
        )}
      </svg>
    </div>
  );
}

// --- Main Dashboard component ---
export default function Dashboard() {
  const { scope, setLastUpdated } = useAppContext();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await fetchDashboard(scope);
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
  }, [scope, setLastUpdated]);

  if (loading) {
    return (
      <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0b1326' }}>
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[0, 1, 2].map(i => <Skeleton key={i} className="h-24 rounded-lg bg-slate-800" />)}
        </div>
        <Skeleton className="h-48 rounded-lg bg-slate-800 mb-4" />
        <div className="grid grid-cols-2 gap-4 mb-4">
          {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-48 rounded-lg bg-slate-800" />)}
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

  if (!data || data.counts.entities === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ backgroundColor: '#0b1326' }}>
        <h2 className="text-base font-semibold text-white">No knowledge yet.</h2>
        <p className="text-slate-400 text-sm">Run <code className="text-blue-400">recall add</code> or <code className="text-blue-400">recall index</code> to populate.</p>
      </div>
    );
  }

  // Build heatmap data from episodes by day
  const episodesByDay = data.recent_episodes.reduce<Record<string, number>>((acc, ep) => {
    const day = ep.created_at?.slice(0, 10) ?? '';
    if (day) acc[day] = (acc[day] ?? 0) + 1;
    return acc;
  }, {});
  const heatmapData = Object.entries(episodesByDay).map(([day, count]) => ({ day, count }));

  // Entity type donut data
  const entityTypeData = Object.entries(data.entity_types).map(([name, value]) => ({
    name, value, color: ENTITY_TYPE_COLORS[name] ?? ENTITY_TYPE_COLORS['Entity'],
  }));

  // Episode sources donut data
  const sourcesData = Object.entries(data.sources).map(([name, value]) => ({
    name, value, color: SOURCE_COLORS[name] ?? '#94a3b8',
  }));

  // Retention donut data
  const retentionData = [
    { name: 'Pinned', value: data.retention.pinned, color: RETENTION_COLORS['Pinned'] },
    { name: 'Normal', value: data.retention.normal, color: RETENTION_COLORS['Normal'] },
    { name: 'Stale', value: data.retention.stale, color: RETENTION_COLORS['Stale'] },
    { name: 'Archived', value: data.retention.archived, color: RETENTION_COLORS['Archived'] },
  ].filter(d => d.value > 0);

  return (
    <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0b1326' }}>
      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard label="Entities" value={data.counts.entities} />
        <StatCard label="Edges" value={data.counts.edges} />
        <StatCard label="Episodes" value={data.counts.episodes} />
      </div>

      {/* Knowledge Growth line chart */}
      <Card className="p-4 mb-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
        <h2 className="text-sm font-semibold text-white mb-3">Knowledge Growth (30 days)</h2>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data.time_series}>
            <XAxis dataKey="day" stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
            <Tooltip contentStyle={{ backgroundColor: '#222a3d', border: 'none', color: '#e2e8f0' }} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            <Line type="monotone" dataKey="entity_count" name="Entities" stroke="#60a5fa" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="edge_count" name="Edges" stroke="#a78bfa" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="episode_count" name="Episodes" stroke="#34d399" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Activity Heatmap */}
      <Card className="p-4 mb-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
        <h2 className="text-sm font-semibold text-white mb-3">Activity (12 months)</h2>
        <ActivityHeatmap data={heatmapData} />
      </Card>

      {/* Charts row: Episode Sources + Entity Types + Top Entities + Retention */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Episode Sources donut */}
        <Card className="p-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
          <h2 className="text-sm font-semibold text-white mb-3">Episode Sources</h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={sourcesData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} dataKey="value">
                {sourcesData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#222a3d', border: 'none', color: '#e2e8f0' }} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Entity Type Distribution donut */}
        <Card className="p-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
          <h2 className="text-sm font-semibold text-white mb-3">Entity Types</h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={entityTypeData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} dataKey="value">
                {entityTypeData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#222a3d', border: 'none', color: '#e2e8f0' }} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Top Connected Entities horizontal bar */}
        <Card className="p-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
          <h2 className="text-sm font-semibold text-white mb-3">Top Connected Entities</h2>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={data.top_entities} layout="vertical">
              <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis type="category" dataKey="name" width={80} stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <Tooltip contentStyle={{ backgroundColor: '#222a3d', border: 'none', color: '#e2e8f0' }} />
              <Bar dataKey="edge_count" name="Edges" fill="#60a5fa" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Retention Status donut */}
        <Card className="p-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
          <h2 className="text-sm font-semibold text-white mb-3">Retention Status</h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={retentionData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} dataKey="value">
                {retentionData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#222a3d', border: 'none', color: '#e2e8f0' }} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Recent Activity Feed */}
      <Card className="p-4" style={{ backgroundColor: '#222a3d', border: 'none' }}>
        <h2 className="text-sm font-semibold text-white mb-3">Recent Activity</h2>
        {data.recent_episodes.length === 0 ? (
          <p className="text-slate-500 text-sm">No recent episodes.</p>
        ) : (
          <ul className="space-y-1">
            {data.recent_episodes.map((ep) => (
              <li
                key={ep.uuid}
                className="flex items-start gap-4 px-3 py-3 rounded-md transition-colors hover:bg-[#171f33]"
              >
                <div
                  className="w-2 h-2 mt-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: SOURCE_COLORS[ep.source] ?? '#94a3b8' }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{ep.source_description || ep.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5 uppercase tracking-tighter">{ep.source || 'cli-add'} • {ep.created_at?.slice(0, 10) ?? ''}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
