# MOSAIC Architecture

## System Diagram

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

## Core Stack
- **Frontend**: React + Vite + TypeScript
- **Backend**: FastAPI (Python)
- **Database**: SQLite (Persistent Event Store)
- **Optimizer**: Google OR-Tools (RoutingModel)

## Recovery Plan Evaluation
Candidate strategies are evaluated under hard feasibility constraints and ranked using SLA, delivery delay, recovery cost, transfers and resource utilization; rescue is used when no feasible piggyback exists.

1. **Hard feasibility**: Capacity, Time windows, Compatibility, Transfer sync, SLA
2. **Delivery delay**
3. **Incremental recovery cost**
4. **Number of transfers**
5. **Extra distance**
