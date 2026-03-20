import { Skeleton } from '@/components/ui/skeleton';

export default function Dashboard() {
  return (
    <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0f172a' }}>
      <h1 className="text-base font-semibold text-white mb-4">Dashboard</h1>
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[0, 1, 2].map(i => <Skeleton key={i} className="h-24 rounded-lg bg-slate-800" />)}
      </div>
      <Skeleton className="h-48 rounded-lg bg-slate-800 mb-4" />
      <Skeleton className="h-48 rounded-lg bg-slate-800" />
    </div>
  );
}
