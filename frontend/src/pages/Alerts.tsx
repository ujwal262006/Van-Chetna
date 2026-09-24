import { useState, useCallback, useEffect } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import AlertFeed from '../components/alerts/AlertFeed';
import AlertDetail from '../components/alerts/AlertDetail';
import { Alert } from '../types';
import { useAlerts } from '../hooks/useAlerts';
import { useLiveAlerts } from '../hooks/useLiveAlerts';
import { getAlerts } from '../services/api';

const HAZARD_NODES = ['URB01', 'RIV01', 'FOR01'];
const ACOUSTIC_NODES = ['NODE_01', 'NODE_02', 'NODE_03', 'NODE_04'];

type FilterTab = 'all' | 'hazard' | 'acoustic' | 'critical' | 'medium';

const TAB_LABELS: Record<FilterTab, string> = {
  all:      'All',
  hazard:   '🔥 Hazard Nodes',
  acoustic: '🎙 Acoustic/Vision',
  critical: '🔴 Critical',
  medium:   '🟡 Medium',
};

export default function Alerts() {
  const { alerts: allAlerts, loading: baseLoading, pushAlert, acknowledge } = useAlerts();
  const [selected, setSelected] = useState<Alert | null>(null);
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [filteredAlerts, setFilteredAlerts] = useState<Alert[]>([]);
  const [filterLoading, setFilterLoading] = useState(false);

  const { connectionState } = useLiveAlerts(useCallback((a: Alert) => pushAlert(a), [pushAlert]));

  // Re-fetch with server-side filter when tab changes
  useEffect(() => {
    if (activeTab === 'all') {
      setFilteredAlerts(allAlerts);
      return;
    }

    setFilterLoading(true);

    if (activeTab === 'critical' || activeTab === 'medium') {
      getAlerts({ severity: activeTab, limit: 100 })
        .then(setFilteredAlerts)
        .finally(() => setFilterLoading(false));
      return;
    }

    // For hazard/acoustic tabs, fetch all then client-filter by node_id
    // (avoids needing a multi-value node_id param on the backend)
    getAlerts({ limit: 200 })
      .then(data => {
        const nodes = activeTab === 'hazard' ? HAZARD_NODES : ACOUSTIC_NODES;
        setFilteredAlerts(data.filter(a => nodes.includes(a.node_id)));
      })
      .finally(() => setFilterLoading(false));
  }, [activeTab, allAlerts]);

  const displayed = activeTab === 'all' ? allAlerts : filteredAlerts;
  const loading = baseLoading || filterLoading;

  return (
    <DashboardLayout title="Alerts" connectionState={connectionState}>
      <div className="max-w-3xl space-y-3">

        {/* Filter tabs */}
        <div className="flex flex-wrap gap-1.5">
          {(Object.keys(TAB_LABELS) as FilterTab[]).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-emerald-600 text-white'
                  : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
              }`}
            >
              {TAB_LABELS[tab]}
              {tab === 'all' && allAlerts.length > 0 && (
                <span className="ml-1.5 text-[10px] bg-white/10 px-1 rounded">
                  {allAlerts.filter(a => a.severity !== 'low').length}
                </span>
              )}
              {tab === 'hazard' && (
                <span className="ml-1.5 text-[10px] bg-white/10 px-1 rounded">
                  {allAlerts.filter(a => HAZARD_NODES.includes(a.node_id) && a.severity !== 'low').length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Node filter hint */}
        {activeTab === 'hazard' && (
          <p className="text-[10px] text-gray-500 italic px-0.5">
            Showing alerts from URB01 (air quality), RIV01 (water level), FOR01 (fire/smoke)
          </p>
        )}
        {activeTab === 'acoustic' && (
          <p className="text-[10px] text-gray-500 italic px-0.5">
            Showing alerts from NODE_01–04 (acoustic / vision)
          </p>
        )}

        <AlertFeed
          alerts={displayed}
          loading={loading}
          onAlertClick={setSelected}
        />
      </div>

      {selected && (
        <AlertDetail
          alert={selected}
          onClose={() => setSelected(null)}
          onAcknowledge={id => {
            acknowledge(id, 'Officer Priya');
            setSelected(prev => prev ? { ...prev, acknowledged: true, acknowledged_by: 'Officer Priya' } : null);
          }}
        />
      )}
    </DashboardLayout>
  );
}
