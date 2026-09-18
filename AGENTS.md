# MOSAIC Agent Rules

You are building MOSAIC per docs/architecture.md. Follow these rules without exception:

1. Work ONE block at a time, from the prompt given to you. Do not implement anything
   from a later block early, even if it seems convenient. Do not "improve" the spec.
2. Every number, percentage, cost, ETA, or score shown anywhere in the frontend MUST
   originate from a backend computation (simulator, DB, solver, or bench run). If you
   cannot compute a value yet, show "not yet computed" or omit it — never invent a
   plausible-looking number.
3. No LLM call may decide feasibility, cost, routing, or any recovery decision. LLM use
   is restricted to: parsing a natural-language disruption into a structured event
   (schema-validated before use). Everything downstream of that is deterministic code.
4. After finishing a block: run the block's tests, run the full test suite, and only
   commit if both pass. Commit message format: `[Block N] <what changed>`. One commit
   per logical change within the block is fine — do not squash into one mega-commit.
5. If a block's acceptance criteria cannot be met (e.g. OR-Tools can't express a
   constraint), STOP and report the exact blocker instead of silently approximating
   and claiming it works.
6. Never claim a metric, benchmark result, or test count that hasn't actually been run
   in this repo. If asked to report results, run the code and report what it prints.
7. Keep the optimization priority hierarchy exactly as specified (SLA feasibility >
   delay > cost > transfers > distance) — not a weighted sum, an actual hierarchy
   (lexicographic or staged optimization).
8. Frontend components read from the `RecoveryPlan`/`DecisionReceipt` API response
   shape only. No duplicated business logic in the frontend (no re-deriving cost or
   feasibility in JS/TS).
