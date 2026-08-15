import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Map, Bell, Radio, Activity, BarChart3, Settings, TreePine } from 'lucide-react';
import ConnectionStatus from '../ui/ConnectionStatus';
import { ConnectionState } from '../../types';

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/map', label: 'Live Map', icon: Map },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/events', label: 'Events', icon: Activity },
  { to: '/nodes', label: 'Sensor Nodes', icon: Radio },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const;

export default function Sidebar({ connectionState }: { connectionState: ConnectionState }) {
  return (
    <aside className="w-56 bg-white dark:bg-[#0a0e12] border-r border-gray-200 dark:border-white/5 flex flex-col h-full shrink-0">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-gray-200 dark:border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
            <TreePine size={16} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-900 dark:text-gray-100 leading-none">Van-Chetna</h1>
            <p className="text-[10px] text-gray-500 dark:text-gray-600 mt-0.5">Forest Guard</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => [
              'flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-medium transition-colors border',
              isActive
                ? 'bg-emerald-50 dark:bg-emerald-600/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-600/20'
                : 'text-gray-600 dark:text-gray-500 hover:text-gray-900 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/[0.02] border-transparent',
            ].join(' ')}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-200 dark:border-white/5 space-y-2">
        <ConnectionStatus state={connectionState} />
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-700/30 flex items-center justify-center">
            <span className="text-[9px] font-bold text-emerald-700 dark:text-emerald-400">PK</span>
          </div>
          <span className="text-[11px] text-gray-600 dark:text-gray-500">Officer Priya</span>
        </div>
      </div>
    </aside>
  );
}
