const API_BASE = 'http://localhost:8000/api';

export interface Hub {
  id: string;
  name: string;
  lat: number;
  lon: number;
}

export interface Vehicle {
  id: string;
  current_location: string;
  shift_start: string;
  shift_end: string;
  max_weight: number;
  max_volume: number;
  schedule: any[];
}

export interface Shipment {
  id: string;
  weight: number;
  volume: number;
  origin: string;
  destination: string;
  current_location: string;
  status: string;
  sla_deadline: string;
}

export interface WorldState {
  state_version: number;
  shipments: string[]; // IDs
  vehicles: string[];
  hubs: string[];
}

export const api = {
  async getState(): Promise<WorldState> {
    const res = await fetch(`${API_BASE}/state`);
    return res.json();
  },
  
  async getShipments(): Promise<Shipment[]> {
    const res = await fetch(`${API_BASE}/shipments`);
    return res.json();
  },
  
  async getVehicles(): Promise<Vehicle[]> {
    const res = await fetch(`${API_BASE}/vehicles`);
    return res.json();
  },
  
  async getHubs(): Promise<Hub[]> {
    const res = await fetch(`${API_BASE}/hubs`);
    return res.json();
  },
  
  async injectDisruption(type: string, payload: any) {
    const res = await fetch(`${API_BASE}/disruptions/inject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ disruption_type: type, payload })
    });
    return res.json();
  },

  async generateRecovery(shipmentId: string) {
    const res = await fetch(`${API_BASE}/recovery/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shipment_id: shipmentId })
    });
    return res.json();
  },

  async getActiveRecovery(shipmentId: string) {
    const res = await fetch(`${API_BASE}/recovery/${shipmentId}/active`);
    if (!res.ok) return null;
    return res.json();
  },

  async getPlans(shipmentId: string) {
    const res = await fetch(`${API_BASE}/recovery/${shipmentId}/plans`);
    return res.json();
  },

  async approvePlan(planId: string) {
    const res = await fetch(`${API_BASE}/recovery/${planId}/approve`, {
      method: 'POST'
    });
    return res.json();
  }
};
