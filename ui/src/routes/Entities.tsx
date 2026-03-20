import { Skeleton } from '@/components/ui/skeleton';

export default function Entities() {
  return (
    <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0f172a' }}>
      <h1 className="text-base font-semibold text-white mb-4">Entities</h1>
      {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-12 rounded bg-slate-800 mb-2" />)}
    </div>
  );
}
