import { Skeleton } from '@/components/ui/skeleton';

export default function Episodes() {
  return (
    <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0f172a' }}>
      <h1 className="text-base font-semibold text-white mb-4">Episodes</h1>
      {[0, 1, 2].map(i => <Skeleton key={i} className="h-28 rounded-lg bg-slate-800 mb-3" />)}
    </div>
  );
}
