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
      style={{ backgroundColor: '#131b2e' }}
    >
      <div className="p-4" style={{ paddingBottom: '12px' }}>
        <span className="text-sm font-semibold tracking-wide" style={{ color: '#7bd0ff' }}>recall</span>
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
                    : 'text-slate-400 hover:text-slate-200 border-l-[3px] border-transparent transition-colors duration-150'
                )}
                style={isActive ? { borderLeftColor: '#7bd0ff', backgroundColor: 'rgba(123,208,255,0.08)' } : {}}
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
