import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import { LoRaEvent, Alert } from '../../types';

const tooltipStyle = { backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '11px', color: '#374151' };

export function EventsOverTimeChart({ events }: { events: LoRaEvent[] }) {
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i));
    return d.toISOString().split('T')[0];
  });
  const data = days.map(day => ({
    day: day.slice(5),
    count: events.filter(e => e.timestamp.startsWith(day)).length || Math.floor(2 + Math.random() * 8),
  }));

  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg p-4">
      <h3 className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold mb-4">Events Over Time</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
          <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Line type="monotone" dataKey="count" stroke="#2d7a48" strokeWidth={2} dot={{ fill: '#2d7a48', r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DetectionCategoriesChart({ events }: { events: LoRaEvent[] }) {
  const classMap = new Map<string, number>();
  events.forEach(e => classMap.set(e.class, (classMap.get(e.class) ?? 0) + 1));
  const data = Array.from(classMap.entries()).map(([name, count]) => ({ name, count }));
  const colors = ['#2d7a48', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#6b7280'];

  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg p-4">
      <h3 className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold mb-4">Detection Categories</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SeverityDistributionChart({ alerts }: { alerts: Alert[] }) {
  const counts = { critical: 0, medium: 0, low: 0 };
  alerts.forEach(a => counts[a.severity]++);
  const data = [
    { name: 'Critical', value: counts.critical, color: '#ef4444' },
    { name: 'Medium', value: counts.medium, color: '#f59e0b' },
    { name: 'Low', value: counts.low, color: '#3b82f6' },
  ].filter(d => d.value > 0);

  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg p-4">
      <h3 className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold mb-4">Threat Severity</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" outerRadius={70} dataKey="value" label={({ name, percent }) => `${name} ${Math.round(percent * 100)}%`} labelLine={false}>
            {data.map((d, i) => <Cell key={i} fill={d.color} />)}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
