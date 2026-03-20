import { useSearchParams } from 'react-router-dom';

export default function Search() {
  const [params] = useSearchParams();
  const q = params.get('q') ?? '';
  return (
    <div className="flex-1 p-6 overflow-auto" style={{ backgroundColor: '#0f172a' }}>
      <h1 className="text-base font-semibold text-white mb-4">
        {q ? `Search results for "${q}"` : 'Search'}
      </h1>
      <p className="text-slate-400 text-sm">Results loading...</p>
    </div>
  );
}
