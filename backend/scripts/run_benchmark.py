import os
import sys
import argparse
import json
from datetime import datetime

# Add the project root to sys.path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db import Base
from app.bench.parser import parse_solomon
from app.bench.transformer import create_scenario
from app.bench.runner import run_recovery_bench

def main():
    parser = argparse.ArgumentParser(description="Run MOSAIC RecoveryBench")
    parser.add_argument("--scenarios", type=int, default=20, help="Number of scenarios to run")
    args = parser.parse_args()

    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'bench', 'data', 'c101.txt'))
    print(f"Loading VRPTW instance: {data_path}")
    instance = parse_solomon(data_path)

    # In-memory DB for rapid benchmarking
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    mosaic_stats = {"successes": 0, "sla_violations": 0, "costs": [], "distances": [], "latencies": []}
    baseline_stats = {"successes": 0, "sla_violations": 0, "costs": [], "distances": [], "latencies": []}

    print(f"Running {args.scenarios} Scenarios...\n")
    
    for i in range(args.scenarios):
        # 1. Reset DB
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        
        # 2. Transform into MOSAIC network (Seed varies per scenario)
        disrupted_ids = create_scenario(db, instance, seed=1000 + i, num_shipments_to_disrupt=1)
        
        # 3. Benchmark
        res = run_recovery_bench(db, disrupted_ids[0])
        
        # Aggregation
        for model_name, stats, m_res in [("MOSAIC", mosaic_stats, res["mosaic"]), ("Baseline", baseline_stats, res["baseline"])]:
            if m_res["success"]:
                stats["successes"] += 1
                if m_res["sla_violation"]:
                    stats["sla_violations"] += 1
                stats["costs"].append(m_res["cost"])
                stats["distances"].append(m_res["distance"])
            stats["latencies"].append(m_res["latency"])
            
        db.close()

    def summarize(stats, total):
        success_rate = (stats["successes"] / total) * 100 if total else 0
        sla_rate = (stats["sla_violations"] / stats["successes"]) * 100 if stats["successes"] else 0
        avg_cost = sum(stats["costs"]) / len(stats["costs"]) if stats["costs"] else 0
        avg_dist = sum(stats["distances"]) / len(stats["distances"]) if stats["distances"] else 0
        avg_lat = sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0
        return success_rate, sla_rate, avg_cost, avg_dist, avg_lat

    ms, m_sla, m_c, m_d, m_l = summarize(mosaic_stats, args.scenarios)
    bs, b_sla, b_c, b_d, b_l = summarize(baseline_stats, args.scenarios)

    print("-" * 100)
    print(f"{'Metric':<30} | {'MOSAIC (CP-SAT)':<25} | {'Baseline (Nearest Feasible)':<25}")
    print("-" * 100)
    print(f"{'Recovery Success Rate':<30} | {ms:>23.1f}% | {bs:>24.1f}%")
    print(f"{'SLA Violation Rate':<30} | {m_sla:>23.1f}% | {b_sla:>24.1f}%")
    print(f"{'Incremental Cost (Avg)':<30} | ${m_c:>22.2f} | ${b_c:>23.2f}")
    print(f"{'Incremental Distance (Avg)':<30} | +{m_d:>21.1f}km | +{b_d:>22.1f}km")
    print(f"{'Planning Latency (Avg)':<30} | {m_l:>21.2f}ms | {b_l:>22.2f}ms")
    print("-" * 100)

    # Save to disk
    out_file = "benchmark_results.json"
    with open(out_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "scenarios": args.scenarios,
            "mosaic": {"success_rate": ms, "sla_violation_rate": m_sla, "avg_cost": m_c, "avg_distance": m_d, "avg_latency_ms": m_l},
            "baseline": {"success_rate": bs, "sla_violation_rate": b_sla, "avg_cost": b_c, "avg_distance": b_d, "avg_latency_ms": b_l}
        }, f, indent=2)
        
    print(f"\nResults saved to {out_file}")

if __name__ == "__main__":
    main()
