import { Skeleton } from '@/components/ui/skeleton';

export default function GraphView() {
  return (
    <div className="flex-1 relative" style={{ backgroundColor: '#0f172a' }}>
      <Skeleton className="absolute inset-0 m-4 rounded-lg bg-slate-800" />
      <div className="absolute inset-0 flex items-center justify-center">
        <p className="text-slate-500 text-sm">Graph loading...</p>
      </div>
    </div>
  );
}
