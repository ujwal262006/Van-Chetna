import { LucideIcon } from 'lucide-react';

interface Props {
  label: string;
  value: string | number;
  icon: LucideIcon;
  color?: string;
}

export default function StatCard({ label, value, icon: Icon, color = 'text-emerald-600 dark:text-emerald-400' }: Props) {
  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg p-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-lg bg-gray-50 dark:bg-white/[0.03] border border-gray-200 dark:border-white/5 flex items-center justify-center ${color}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-[11px] uppercase tracking-wider text-gray-500 font-medium">{label}</p>
        <p className={`font-mono text-xl font-bold mt-0.5 ${color}`}>{value}</p>
      </div>
    </div>
  );
}
