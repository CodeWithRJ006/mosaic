# MOSAIC Jury Q&A

**Q: How does MOSAIC handle "bullwhip" or cascading delays?**
A: We implemented a strict "Delay Cascade Check" in the `HardConstraintFilter` (Block 3). When evaluating a recovery route, MOSAIC verifies if delaying a vehicle to pick up the stranded shipment will violate the SLA of *any* shipments already scheduled on that vehicle. If it does, the candidate is instantly rejected. Recovery must be zero-impact to existing commitments.

**Q: Is the frontend calculating any of these ETA or Cost numbers?**
A: No. As per our core architectural rules, the frontend is strictly a visualization layer. Every number shown (ETAs, Incremental Cost, SLA margins, rejected candidate breakdown) is computed by the backend `ORToolsOptimizer` and `HardConstraintFilter`, persisted to the DB via `StateManager`, and served via the `DecisionReceipt` payload.

**Q: Why use Google OR-Tools CP-SAT instead of RoutingModel?**
A: `RoutingModel` is built for creating initial daily routes. Recovery is a discrete allocation and capacity problem: we have a fixed graph of existing moving capacity, and we need to bin-pack disrupted shipments into remaining space under hard temporal constraints. CP-SAT is mathematically native to this exact type of constrained discrete allocation problem, allowing us to enforce a strict lexicographic hierarchy (Feasibility > Delay > Cost > Transfers).

**Q: What happens if two disruptions happen at the exact same time? (Concurrency)**
A: MOSAIC implements a global `state_version` (Block 2). When a plan is submitted for approval, the API verifies `plan.state_version == current global state_version`. If another disruption changed the graph in the milliseconds since the plan was generated, the plan flips to `INVALIDATED` and the engine dynamically replans, preventing double-booking of scarce recovery capacity.

**Q: How do you prove this actually saves money?**
A: We built `RecoveryBench` (Block 11), a benchmarking suite that runs standard VRPTW (Vehicle Routing Problem with Time Windows) datasets. For every incident, we calculate the CP-SAT recovery plan and contrast it against a "Baseline Counterfactual" (a naive nearest-feasible heuristic). The delta in incremental distance and cost provides mathematically verifiable proof of operational savings.

**Q: Are LLMs making logistics decisions?**
A: No. LLM utilization is explicitly restricted. AI is only used to parse natural-language disruption text into structured JSON event payloads. Once an event is emitted into the bus, 100% of the downstream routing, feasibility, capacity checking, and cost optimization is handled by deterministic, auditable code.
