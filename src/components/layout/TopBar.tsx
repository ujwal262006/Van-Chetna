import { Bell, User, Sun, Moon } from 'lucide-react';
import ConnectionStatus from '../ui/ConnectionStatus';
import { ConnectionState } from '../../types';
import { useTheme } from '../../hooks/useTheme';

interface Props {
  title: string;
  connectionState: ConnectionState;
  alertCount?: number;
}

export default function TopBar({ title, connectionState, alertCount = 0 }: Props) {
  const { theme, toggle } = useTheme();

  return (
    <header className="h-14 bg-white dark:bg-[#0a0e12] border-b border-gray-200 dark:border-white/5 px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-4">
        <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-200">{title}</h2>
        <span className="text-[10px] text-emerald-600 dark:text-gray-600 uppercase tracking-wider hidden md:inline">
          ● SYSTEM ONLINE
        </span>
      </div>

      <div className="flex items-center gap-4">
        <ConnectionStatus state={connectionState} />

        {/* Theme toggle */}
        <button
          onClick={toggle}
          className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
          title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        >
          {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
        </button>

        <button className="relative text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
          <Bell size={18} />
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
              {alertCount > 9 ? '9+' : alertCount}
            </span>
          )}
        </button>

        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 flex items-center justify-center">
            <User size={14} className="text-gray-500 dark:text-gray-400" />
          </div>
          <span className="text-xs text-gray-600 dark:text-gray-500 hidden sm:inline">Priya K.</span>
        </div>
      </div>
    </header>
  );
}
