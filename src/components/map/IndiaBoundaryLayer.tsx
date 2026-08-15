import { useEffect, useState } from 'react';
import { GeoJSON } from 'react-leaflet';
import type { GeoJsonObject } from 'geojson';

/**
 * India political boundary from Survey of India.
 * Loaded from /india-boundary.geojson (public/ directory).
 * Renders as independent layer — can be toggled without affecting other layers.
 */
export default function IndiaBoundaryLayer({ visible = true }: { visible?: boolean }) {
  const [data, setData] = useState<GeoJsonObject | null>(null);

  useEffect(() => {
    if (!visible) return;
    fetch('/india-boundary.geojson')
      .then(r => r.ok ? r.json() : null)
      .then(geojson => { if (geojson) setData(geojson as GeoJsonObject); })
      .catch(() => {});
  }, [visible]);

  if (!visible || !data) return null;

  return (
    <GeoJSON
      key="india-boundary"
      data={data}
      style={{ color: '#2d7a48', weight: 2.5, opacity: 0.9, fillOpacity: 0 }}
    />
  );
}
