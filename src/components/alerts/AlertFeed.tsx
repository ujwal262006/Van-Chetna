import AlertCard from './AlertCard';
import LoadingState from '../ui/LoadingState';
import EmptyState from '../ui/EmptyState';
import { Alert } from '../../types';

interface Props {
  alerts: Alert[];
  loading: boolean;
  onAlertClick: (alert: Alert) => void;
  recentIds?: Set<number>;
}

export default function AlertFeed({ alerts, loading, onAlertClick, recentIds }: Props) {
  // Only show critical and medium in the live feed
  const active = alerts.filter(a => a.severity !== 'low');

  if (loading) return <LoadingState message="Loading alerts..." />;
  if (active.length === 0) return <EmptyState />;

  return (
    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
      {active.map(alert => (
        <AlertCard key={alert.id} alert={alert} onClick={onAlertClick} isNew={recentIds?.has(alert.id)} />
      ))}
    </div>
  );
}
