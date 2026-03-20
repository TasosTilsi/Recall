import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Network, Database, GitBranch, BookOpen } from 'lucide-react';

const TABS = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Graph', path: '/graph', icon: Network },
  { label: 'Entities', path: '/entities', icon: Database },
  { label: 'Relations', path: '/relations', icon: GitBranch },
  { label: 'Episodes', path: '/episodes', icon: BookOpen },
];

export function Sidebar() {
  const { pathname } = useLocation();
  return (
    <nav
      className="flex flex-col w-[200px] flex-shrink-0 h-full"
      style={{ backgroundColor: '#1e293b', borderRight: '1px solid #334155' }}
    >
      <div className="p-4 border-b" style={{ borderColor: '#334155' }}>
        <span className="text-sm font-semibold text-white tracking-wide">recall</span>
      </div>
      <ul className="flex-1 overflow-y-auto py-2">
        {TABS.map(({ label, path, icon: Icon }) => {
          const isActive = path === '/' ? pathname === '/' : pathname.startsWith(path);
          return (
            <li key={path}>
              <Link
                to={path}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 text-sm transition-colors',
                  isActive
                    ? 'text-white font-medium border-l-[3px]'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50 border-l-[3px] border-transparent'
                )}
                style={isActive ? { borderLeftColor: '#3b82f6', backgroundColor: '#334155' } : {}}
              >
                <Icon size={16} />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
