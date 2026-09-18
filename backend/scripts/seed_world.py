import os
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db import Base, Hub, Vehicle, Shipment
from app.simulator.scenario import ScenarioGenerator

def get_engine():
    db_url = os.getenv("DATABASE_URL", "postgresql://mosaic_user:mosaic_password@localhost:5432/mosaic_db")
    return create_engine(db_url)

def main():
    parser = argparse.ArgumentParser(description="Seed MOSAIC deterministic world.")
    parser.add_argument("--seed", type=int, default=58291, help="Seed for the generator")
    args = parser.parse_args()

    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    gen = ScenarioGenerator(args.seed)
    hubs, vehicles, shipments = gen.generate()
    
    with SessionLocal() as db:
        # Clear existing
        db.query(Shipment).delete()
        db.query(Vehicle).delete()
        db.query(Hub).delete()
        
        # Insert new
        db.add_all(hubs)
        db.add_all(vehicles)
        db.add_all(shipments)
        
        db.commit()
        
        print(f"World seeded deterministically (seed={args.seed})!")
        print(f"Hubs: {len(hubs)}")
        print(f"Vehicles: {len(vehicles)}")
        print(f"Shipments: {len(shipments)}")

if __name__ == "__main__":
    main()
