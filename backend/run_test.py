from datetime import datetime, timezone, timedelta
from app.db import SessionLocal
from app.models.db import Event
from sqlalchemy import func

db = SessionLocal()
latest = db.query(func.max(Event.timestamp)).scalar()
print('Latest:', latest)
