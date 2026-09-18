import sqlite3
import json
from typing import List
from datetime import datetime
from backend.app.models.events import Event, EventType

class EventStore:
    def __init__(self, db_path: str = "mosaic.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    state_version INTEGER NOT NULL
                )
            """)
            conn.commit()

    def append(self, event: Event):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (id, type, timestamp, payload, state_version) VALUES (?, ?, ?, ?, ?)",
                (event.id, event.type.value, event.timestamp.isoformat(), json.dumps(event.payload), event.state_version)
            )
            conn.commit()

    def get_all(self) -> List[Event]:
        events = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, type, timestamp, payload, state_version FROM events ORDER BY state_version ASC")
            for row in cursor:
                events.append(Event(
                    id=row[0],
                    type=EventType(row[1]),
                    timestamp=datetime.fromisoformat(row[2]),
                    payload=json.loads(row[3]),
                    state_version=row[4]
                ))
        return events
