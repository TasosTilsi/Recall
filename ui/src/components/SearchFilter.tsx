'use client';

interface Props {
  search: string; onSearch: (v: string) => void;
  typeFilter: string; onTypeFilter: (v: string) => void;
  entityTypes: string[];
}

export default function SearchFilter({ search, onSearch, typeFilter, onTypeFilter, entityTypes }: Props) {
  return (
    <div className="flex gap-2">
      <input value={search} onChange={e => onSearch(e.target.value)}
        placeholder="Search nodes..." className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200 placeholder-slate-500 w-40" />
      <select value={typeFilter} onChange={e => onTypeFilter(e.target.value)}
        className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200">
        <option value="">All types</option>
        {entityTypes.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
    </div>
  );
}
