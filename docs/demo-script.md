# MOSAIC Demo Script

This script walks through the core capabilities of the MOSAIC Recovery Engine.

## Phase 1: Normal Operations (Control Tower)
1. **Open the Control Tower (`http://localhost:5173`)**
   - Note the live MapLibre interface showing Hubs and active scheduled vehicle locations.
   - Note the active metrics (Active Incidents, SLA At Risk). Currently, everything is nominal.

## Phase 2: Injecting Chaos (Judge Mode)
1. **Open Judge Mode (`http://localhost:5173/judge`)**
   - We will simulate a real-world supply chain failure.
   - Click **"Misroute Shipment (SHP_001 → HUB_9)"** to force a package to the wrong terminal.
2. **Observe Real-Time Event Bus**
   - Return to the Control Tower. Note the "Active Incidents" metric immediately ticks up to 1. 
   - A misrouted shipment alert appears below the map.

## Phase 3: Incident Details
1. **Click on the Disrupted Shipment**
   - Navigates to the Incident Screen (`/incident/:id`).
   - Here we see the mathematical discrepancy: The shipment's intended route has broken. The shipment is stranded, and the SLA deadline is ticking down.
2. **Click "Generate Recovery"**
   - This triggers the MOSAIC CP-SAT Engine.
   - The backend `CandidateGenerator` queries the Temporal Capacity Graph for all upcoming vehicles passing near the stranded shipment.
   - The `HardConstraintFilter` eliminates any vehicle that can't fit the box (Weight/Volume check), can't make the transfer time (Time check), or will violate downstream commitments (Delay cascade check).

## Phase 4: Recovery Options & Decision Trace
1. **View Recovery Screen**
   - You are presented with mathematically optimal options:
     - **Primary Plan (Optimal Strategy)**
     - **Shadow Plan (Fallback Strategy)**
   - The metrics shown (ETA, Incremental Cost, Extra Distance, Transfers) are exact calculations from the solver. No mocked numbers.
   - *If no feasible piggyback exists*, a "No Feasible Piggyback" chart renders, displaying a breakdown of exactly *why* candidates were rejected (e.g. "SLA_VIOLATION").
2. **Click "Decision Trace"**
   - This screen provides the cryptographically-verifiable proof of solver decisions.
   - Observe the constraint margins (e.g., `+10 kg` capacity remaining, `+5 min` pickup window).
   - Scroll through the unredacted log of rejected vehicle candidates.
3. **Approve the Plan**
   - Click "Approve Plan". The backend promotes this to the active timeline.

## Phase 5: Network Autopsy
1. **Click "Network Autopsy"**
   - View the historical reconstruction of the incident from the immutable `Event` log.
   - Compare the MOSAIC CP-SAT recovery execution against a **Baseline Counterfactual** (what a naive Nearest-Feasible heuristic routing algorithm would have done).
   - Observe the cost/distance savings directly resulting from MOSAIC's constraint solver logic.
