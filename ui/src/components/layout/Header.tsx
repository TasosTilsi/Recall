import { useNavigate } from 'react-router-dom';
import { useAppContext } from '@/context/AppContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { RefreshCw, Moon, Sun } from 'lucide-react';
import { useState, useEffect } from 'react';

interface HeaderProps {
  onRefresh: () => void;
}

export function Header({ onRefresh }: HeaderProps) {
  const { scope, setScope, lastUpdated } = useAppContext();
  const [searchValue, setSearchValue] = useState('');
  const [isDark, setIsDark] = useState(true);
  const [secondsAgo, setSecondsAgo] = useState<number | null>(null);
  const navigate = useNavigate();

  // Update "X seconds ago" every 5s
  useEffect(() => {
    if (!lastUpdated) return;
    const update = () => setSecondsAgo(Math.floor((Date.now() - lastUpdated.getTime()) / 1000));
    update();
    const id = setInterval(update, 5000);
    return () => clearInterval(id);
  }, [lastUpdated]);

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchValue.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchValue.trim())}`);
    }
    if (e.key === 'Escape') {
      setSearchValue('');
    }
  };

  const toggleTheme = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('dark');
  };

  const updatedLabel = lastUpdated
    ? secondsAgo !== null && secondsAgo < 5
      ? 'Updated just now'
      : `Updated ${secondsAgo}s ago`
    : '';

  return (
    <header
      className="flex items-center px-4 gap-4 flex-shrink-0 z-10"
      style={{ height: '48px', backgroundColor: '#0b1326' }}
    >
      {/* Scope toggle */}
      <ToggleGroup
        type="single"
        value={scope}
        onValueChange={(v) => v && setScope(v as 'project' | 'global')}
        className="flex-shrink-0"
      >
        <ToggleGroupItem value="project" className="text-xs h-7 px-3">Project</ToggleGroupItem>
        <ToggleGroupItem value="global" className="text-xs h-7 px-3">Global</ToggleGroupItem>
      </ToggleGroup>

      {/* Search bar — centered */}
      <div className="flex-1 flex justify-center">
        <Input
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          placeholder="Search entities, facts, episodes..."
          className="max-w-[320px] h-7 text-sm bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
        />
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {updatedLabel && (
          <span className="text-xs text-slate-400">{updatedLabel}</span>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          className="h-7 px-2 text-xs text-slate-400 hover:text-white"
        >
          <RefreshCw size={14} className="mr-1" />
          Refresh Data
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="h-7 w-7 text-slate-400 hover:text-white"
        >
          {isDark ? <Sun size={14} /> : <Moon size={14} />}
        </Button>
      </div>
    </header>
  );
}
