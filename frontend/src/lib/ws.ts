type Listener = (data: any) => void;

export class WSClient {
  private ws: WebSocket | null = null;
  private listeners: Listener[] = [];

  connect() {
    this.ws = new WebSocket('ws://localhost:8000/ws/state');
    
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.listeners.forEach(l => l(data));
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };

    this.ws.onclose = () => {
      setTimeout(() => this.connect(), 1000);
    };
  }

  subscribe(listener: Listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }
}

export const wsClient = new WSClient();
