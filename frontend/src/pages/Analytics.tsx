import DashboardLayout from '../components/layout/DashboardLayout';
import { EventsOverTimeChart, DetectionCategoriesChart, SeverityDistributionChart } from '../components/analytics/AnalyticsCharts';
import LoadingState from '../components/ui/LoadingState';
import { useEvents } from '../hooks/useEvents';
import { useAlerts } from '../hooks/useAlerts';
import { useLiveAlerts } from '../hooks/useLiveAlerts';
import { useCallback } from 'react';

export default function Analytics() {
  const { events, loading: evLoading } = useEvents();
  const { alerts, loading: alLoading } = useAlerts();
  const { connectionState } = useLiveAlerts(useCallback(() => {}, []));

  const loading = evLoading || alLoading;

  return (
    <DashboardLayout title="Analytics" connectionState={connectionState}>
      {loading ? (
        <LoadingState message="Loading analytics..." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <EventsOverTimeChart events={events} />
          <DetectionCategoriesChart events={events} />
          <SeverityDistributionChart alerts={alerts} />
        </div>
      )}
    </DashboardLayout>
  );
}
