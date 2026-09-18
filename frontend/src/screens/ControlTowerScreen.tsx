import { useEffect, useRef, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { api } from '../lib/api';
import type { Hub, Vehicle, Shipment } from '../lib/api';
import { wsClient } from '../lib/ws';
import { AlertCircle, Clock, Search } from 'lucide-react';

export default function ControlTowerScreen() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const navigate = useNavigate();

  const [hubs, setHubs] = useState<Hub[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);

  // We keep markers in refs to easily update their positions without full re-render
  const vehicleMarkers = useRef<{ [id: string]: maplibregl.Marker }>({});
  const shipmentMarkers = useRef<{ [id: string]: maplibregl.Marker }>({});

  const loadData = async () => {
    const [hRes, vRes, sRes] = await Promise.all([
      api.getHubs(),
      api.getVehicles(),
      api.getShipments()
    ]);
    setHubs(hRes);
    setVehicles(vRes);
    setShipments(sRes);
  };

  useEffect(() => {
    loadData();
    const unsub = wsClient.subscribe((msg) => {
      // Refresh on state update
      if (msg.type === 'STATE_UPDATED') {
        loadData();
      }
    });
    return unsub;
  }, []);

  // Hub coordinates index for mapping current_location to lat/lon
  const hubCoords = useMemo(() => {
    const idx: Record<string, [number, number]> = {};
    hubs.forEach(h => {
      idx[h.id] = [h.lon, h.lat];
    });
    return idx;
  }, [hubs]);

  // Init Map
  useEffect(() => {
    if (map.current || !mapContainer.current) return;
    
    const offlineStyle = {
      version: 8 as const,
      sources: {},
      layers: [{
        id: 'background',
        type: 'background',
        paint: { 'background-color': '#0f172a' }
      }]
    };

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: navigator.onLine ? 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json' : offlineStyle,
      center: [-74.0, 40.7], // NY/NJ center (matches data)
      zoom: 9 // Closer zoom since we focus on NY/NJ hubs
    });
    
    map.current.on('error', (e) => {
      // Graceful offline fallback if cartocdn is blocked
      if (e.error && e.error.message && e.error.message.includes('fetch')) {
        map.current?.setStyle(offlineStyle);
      }
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // Render Hubs and fit map to them
  useEffect(() => {
    if (!map.current || hubs.length === 0) return;

    let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;

    hubs.forEach(h => {
      if (h.lat < minLat) minLat = h.lat;
      if (h.lat > maxLat) maxLat = h.lat;
      if (h.lon < minLng) minLng = h.lon;
      if (h.lon > maxLng) maxLng = h.lon;

      const el = document.createElement('div');
      el.className = 'w-4 h-4 rounded-sm bg-slate-700 border border-slate-500';
      el.title = `${h.name} (${h.id})`;
      new maplibregl.Marker({ element: el })
        .setLngLat([h.lon, h.lat])
        .addTo(map.current!);
    });

    if (minLat <= maxLat && minLng <= maxLng) {
      map.current.fitBounds(
        [[minLng, minLat], [maxLng, maxLat]],
        { padding: 80, duration: 1500 }
      );
    }
  }, [hubs]);

  // Render Vehicles
  useEffect(() => {
    if (!map.current || vehicles.length === 0) return;
    
    vehicles.forEach(v => {
      const coords = hubCoords[v.current_location];
      if (!coords) return;
      
      if (!vehicleMarkers.current[v.id]) {
        const el = document.createElement('div');
        el.className = 'w-3 h-3 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]';
        el.title = `Vehicle ${v.id}`;
        vehicleMarkers.current[v.id] = new maplibregl.Marker({ element: el })
          .setLngLat(coords)
          .addTo(map.current!);
      } else {
        vehicleMarkers.current[v.id].setLngLat(coords);
      }
    });
  }, [vehicles, hubCoords]);

  // Render Shipments & Compute Stats
  useEffect(() => {
    if (!map.current || shipments.length === 0) return;

    shipments.forEach(s => {
      const coords = hubCoords[s.current_location];
      if (!coords) return;

      const isDisrupted = s.status === 'MISROUTED' || s.status === 'DELAYED' || s.status === 'EXCEPTION';
      
      if (!shipmentMarkers.current[s.id]) {
        const el = document.createElement('div');
        el.className = `w-2 h-2 rounded-full cursor-pointer transition-transform hover:scale-150 ${isDisrupted ? 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.8)] z-10' : 'bg-blue-400 opacity-60'}`;
        el.title = `${s.id} — ${s.status}`;
        
        el.addEventListener('click', () => {
          navigate(`/incident/${s.id}`);
        });

        shipmentMarkers.current[s.id] = new maplibregl.Marker({ element: el })
          .setLngLat(coords)
          .addTo(map.current!);
      } else {
        const marker = shipmentMarkers.current[s.id];
        marker.setLngLat(coords);
        const el = marker.getElement();
        el.className = `w-2 h-2 rounded-full cursor-pointer transition-transform hover:scale-150 ${isDisrupted ? 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.8)] z-10' : 'bg-blue-400 opacity-60'}`;
      }
    });
  }, [shipments, hubCoords, vehicles, navigate]);

  // Compute stats
  const activeIncidents = shipments.filter(s => s.status === 'MISROUTED' || s.status === 'DELAYED').length;
  // Naive check: if it's disrupted, it's at risk. In reality would check SLA < now
  const slaAtRisk = shipments.filter(s => new Date(s.sla_deadline) < new Date(Date.now() + 4 * 3600 * 1000)).length;
  const opportunities = activeIncidents; // placeholder for unrecovered

  return (
    <div className="flex flex-col h-full relative">
      <div className="absolute top-4 left-4 right-4 z-10 flex gap-4 pointer-events-none">
        
        <div className="bg-slate-900/90 border border-slate-700/50 backdrop-blur rounded-lg p-4 flex flex-col gap-1 w-64 shadow-xl pointer-events-auto">
          <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" /> Active Incidents
          </div>
          <div className="text-3xl font-bold text-white">{activeIncidents}</div>
        </div>
        
        <div className="bg-slate-900/90 border border-slate-700/50 backdrop-blur rounded-lg p-4 flex flex-col gap-1 w-64 shadow-xl pointer-events-auto">
          <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-400" /> SLA At Risk
          </div>
          <div className="text-3xl font-bold text-white">{slaAtRisk}</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-700/50 backdrop-blur rounded-lg p-4 flex flex-col gap-1 w-64 shadow-xl pointer-events-auto">
          <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-2">
            <Search className="w-4 h-4 text-emerald-400" /> Recovery Opps
          </div>
          <div className="text-3xl font-bold text-white">{opportunities}</div>
        </div>

      </div>

      <div ref={mapContainer} className="flex-1 w-full" />
    </div>
  );
}
