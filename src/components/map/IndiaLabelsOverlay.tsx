import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { useEffect } from 'react';

interface LabelDef {
  position: [number, number];
  text: string;
  minZoom: number;
  maxZoom: number;
}

const LABELS: LabelDef[] = [
  { position: [34.8, 75.2], text: 'Jammu & Kashmir', minZoom: 5, maxZoom: 6 },
  { position: [34.2, 74.0], text: 'Jammu & Kashmir', minZoom: 7, maxZoom: 9 },
  { position: [35.9, 75.6], text: 'Jammu & Kashmir', minZoom: 7, maxZoom: 9 },
  { position: [35.0, 78.0], text: 'Ladakh', minZoom: 5, maxZoom: 6 },
  { position: [34.8, 78.2], text: 'Ladakh', minZoom: 7, maxZoom: 9 },
];

function getFontSize(zoom: number) { return zoom <= 5 ? 10 : zoom <= 6 ? 11 : 12; }
function getOpacity(zoom: number) { return zoom <= 5 ? 0.5 : zoom <= 6 ? 0.6 : 0.75; }

export default function IndiaLabelsOverlay() {
  const map = useMap();

  useEffect(() => {
    const markers: L.Marker[] = [];
    const pokBounds = L.latLngBounds([33.5, 73.0], [34.9, 75.8]);
    const gbBounds = L.latLngBounds([34.9, 74.0], [37.1, 77.2]);
    const rectStyle: L.PathOptions = { fillColor: '#080b0f', fillOpacity: 0.8, stroke: false, interactive: false };
    const rect1 = L.rectangle(pokBounds, rectStyle);
    const rect2 = L.rectangle(gbBounds, rectStyle);

    LABELS.forEach(() => {
      markers.push(L.marker([0, 0], { interactive: false, icon: L.divIcon({ html: '', className: '', iconSize: [0, 0] }) }));
    });

    function update() {
      const zoom = map.getZoom();
      if (zoom >= 5 && zoom <= 9) { rect1.addTo(map); rect2.addTo(map); }
      else { rect1.remove(); rect2.remove(); }

      const fontSize = getFontSize(zoom);
      const opacity = getOpacity(zoom);

      LABELS.forEach((def, i) => {
        const m = markers[i];
        if (zoom >= def.minZoom && zoom <= def.maxZoom) {
          m.setLatLng(def.position);
          m.setIcon(L.divIcon({
            html: `<span style="white-space:nowrap;font-family:Inter,system-ui;font-size:${fontSize}px;font-weight:500;color:rgba(180,190,200,${opacity});letter-spacing:1.5px;pointer-events:none;text-shadow:0 0 6px #080b0f,0 0 12px #080b0f;transform:translate(-50%,-50%)">${def.text}</span>`,
            className: '', iconSize: [0, 0], iconAnchor: [0, 0],
          }));
          m.addTo(map);
        } else { m.remove(); }
      });
    }

    map.on('zoomend', update);
    update();
    return () => { map.off('zoomend', update); markers.forEach(m => m.remove()); rect1.remove(); rect2.remove(); };
  }, [map]);

  return null;
}
