# MOSAIC

MOSAIC is a high-performance logistics disruption and recovery engine. It monitors a digital twin of a supply chain network (hubs, vehicles, and shipments) and automatically generates real-time, mathematically optimal recovery plans when disruptions occur (e.g., misrouted shipments, delayed vehicles, closed hubs). 

Built to avoid costly dedicated recovery runs, MOSAIC exhaustively evaluates all possible "piggyback" opportunities on existing in-transit fleet capacity, utilizing Google OR-Tools (CP-SAT) to evaluate complex constraints in real-time.

## Architecture Pipeline

```text
                         MOSAIC
                           │
                  ┌────────▼────────┐
                  │ Scenario Engine │
                  │ Digital Twin    │
                  └────────┬────────┘
                           │
                      Event occurs
                           │
                           ▼
                   ┌───────────────┐
                   │ Event Store   │
                   │ SQLite        │
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ State Manager │
                   │ versioned     │
                   └───────┬───────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ Temporal Recovery        │
              │ Capacity Graph           │
              └────────────┬─────────────┘
                           │
                           ▼
                  Candidate Generation
                           │
                           ▼
                 Hard Feasibility Filter
                           │
                           ▼
                 OR-Tools Route Engine
                           │
                           ▼
                 Feasible Recovery Plans
                           │
                    ┌──────┴──────┐
                    │             │
                 PRIMARY        SHADOW
                    │             │
                    └──────┬──────┘
                           │
                           ▼
                   Decision Receipt
                           │
                           ▼
                       APPROVAL
                           │
                           ▼
                       EXECUTION
                           │
                     state changes
                           │
                           ▼
                  INVALIDATE / REPLAN
```

## Running Locally

Requires Docker and Docker Compose.

1. Clone the repository and navigate to the root directory.
2. Build and start the stack:
   ```bash
   docker compose up --build
   ```
3. Access the Control Tower UI at `http://localhost:5173`
4. Use the built-in "Judge Mode" at `http://localhost:5173/judge` to forcefully inject disruptions into the network.

## Running RecoveryBench

RecoveryBench is our automated testing suite that takes standard VRPTW instances (e.g. Solomon C101), spins up a full MOSAIC simulation, injects disruptions, and evaluates the baseline nearest-feasible algorithm against the full MOSAIC CP-SAT optimizer.

Run the benchmark from within the backend container:

```bash
docker compose exec backend python scripts/run_benchmark.py --scenarios 20
```

This generates `benchmark_results.json` and outputs a precise table mapping success rate, SLA violation rate, and cost/distance reductions.

## Known Limitations

- **Solve-Time Budget**: The CP-SAT solver is strictly bounded to a 2.0 second search limit to ensure UI responsiveness. Highly complex networks may return feasible rather than provably optimal results.
- **Scale Tested**: Currently thoroughly benchmarked with 25-node topologies (e.g. subset of Solomon C101 instances) operating under tight SLA constraints. 
- **Graph Expansion**: Transfer synchronizations are fully checked for time and volume capacity, but currently the candidate generation logic builds direct edge lists. Multi-hop chains rely on pre-scheduled connections rather than synthesizing completely new chained transfers from scratch.
