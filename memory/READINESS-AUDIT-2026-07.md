# Readiness Audit 2026-07 — the redesign-forcing-function audit

**Status: OPEN (ratified 2026-07-19) · Protocol: EXECUTION-PROTOCOL v1.1**

Governing question: **"If Stages 8–15 were built exactly as written, what
would eventually force a stop-and-redesign of the engine?"**

Discipline: evidence-first and proportionality-bounded. Every workstream
answers a concrete engineering question with measurement or file-cited
reading — not prose. Every finding must land as exactly one of: a ratified
decision at a STOP, a `MACRO-ROADMAP.md` ledger row, a protocol amendment,
or a parked-work entry. A finding disposed nowhere keeps the audit open.
Findings carry VERIFIED / LIKELY / UNKNOWN labels per house rules.

Position: closure is a **Stage 9 activation precondition** (recorded in the
macro-roadmap). It is **not** an 8B blocker — W1 is read-only and runs in
parallel with the 8B probes. This audit re-litigates nothing that survived
the 2026-07-14 reconciliation, the 2026-07-15 repo assessment, or the
per-leg adversarial reviews; it targets the unexamined dimensions only.

## W1 — Scale probe (the scaling curve, measured)

Question: what are the actual growth curves of wall-time, memory, DB size,
registry occupancy, and hash cost as agent count and horizon grow — and
which term goes superlinear first?

Method (read-only; probe-runner subagent; scratch DB per the Leg-0 pattern —
purpose-created `DB_NAME`, override verified through the app's own
`load_dotenv` path, dropped after use; output redirected to files):

- Sweep: agent count {scenario baseline, ~2×, ~5×, ~10×} × horizon
  {320, 1,000, ~5,000 ticks}, on probe-only scenario variants of the
  existing harness (`living_agent_harness.py`). Seeds: the recorded
  `living-agents-stage6` plus one alternate.
- Metrics per run: total + per-tick wall-time, peak process memory, DB size
  delta, per-registry entry counts and payload bytes vs caps, hash-compute
  share of tick time, accepted-by-type counts, deaths.
- Output: the measurement table pasted here, plus a fitted growth trend per
  metric with the first superlinear term named.

Rules: no cap is raised — a scaled config that would breach a cap is itself
a finding (record the projected breach point and the stage whose population
implies it). Probe variants are never committed as gate vehicles; the
standing scenario decision remains the 8B contract's to make. If the
scenario/harness cannot parameterise population at all, that inability is
**finding W1-0** (scenario configurability gap) and is reported before any
sweep is attempted.

Feeds: the standing scenario decision (8B STOP), Stage 12A's baseline, the
protocol's from-Stage-9 telemetry rows.

## W2 — Core assumption + future-capability-compatibility scan

Question, part 1 (redesign triggers): does Core contain assumptions that
break under later stages? Scan every Core surface — commit pipeline,
validation authority, hashing, RNG keying, registry infrastructure,
snapshot/persistence, fork/replay/resume, tick scheduling, projection layer
— against the three red flags:

1. anything that later requires **global knowledge**;
2. anything that later requires **retroactive history**;
3. anything that later requires **mutable world truth**;

plus the compounding-cost assumptions: per-tick domain-evaluation cost ×
agent count; hash cost × state size; payload targets × stage stacking.

Question, part 2 (unnecessary constraints — ratified addition 2026-07-19):
**does any current API, data contract, or invariant unnecessarily constrain
a capability currently planned for Stages 9–15?** A surface can pass part 1
and still fail part 2. Checklist, applied per surface:

- event payload size assumptions;
- registry lookup / indexing assumptions;
- fixed relationship cardinality;
- serialization contracts;
- tick scheduling assumptions (incl. engine_priority numbering headroom —
  the 87 < 88 < 89 < 90 pattern must admit ~7 more stages of domains);
- domain boundary assumptions;
- snapshot strategy.

Output format — one finding row per hit: surface · assumption · constrained
capability (stage) · projected breach point · severity · VERIFIED citation
(file:line) · disposition (accept / contract at stage N / redesign flag).
"No blocking flaw" is a valid and expected per-surface verdict (CLAUDE.md
proportionality); do not enumerate non-findings.

## W3 — Gate-metrics upgrade

Question: do gates prove reliability and robustness, not just occurrence?
**Delivered**: EXECUTION-PROTOCOL v1.1 adds the Stability clause (recurrence
/ persistence per a contract-defined measure) and the Robustness clause
(fires under ≥2 seeds; orthogonal to per-seed determinism, which is
unchanged). Directed into the 8B–8D contracts via their own acceptance
gates. Closes when the protocol commit lands and the 8B contract carries
both clauses. Remaining audit work: none beyond that verification.

## W4 — Vision spot-check

Question: do the stage charters 9–15 contradict or orphan anything in the
vision corpus (`PRD.md`, `Domain Plan.txt`, and any original vision docs)?
One pass; contradictions and orphans only — no restatement, no style audit.

Pre-registered findings (already surfaced en route to this audit):

- **W4-1 Religion** — named only as an 8D non-goal; no stage owns it.
  Disposition path: ledger row (open gap, user ruling).
- **W4-2 Content-stage landing** — myths/rituals/symbolic objects/naming
  have a taxonomy category but no owning stage. Ledger row (open gap).
- **W4-3 Language** — no stage 6–15 owns language as a communication
  system; Stage 15 dialogue is presentation, not capacity. Ledger row
  (open gap, user ruling: pre-14 capability leg, 15-scope ruling, or
  out-of-scope).

Closes when the pass is complete and every contradiction/orphan has a
ledger row or ruling.

## W5 — Ordering verification

Question: is the claimed dependency chain **persistent identity → memory →
reputation substrate → transmission** actually closed in code, so 8B/8C
ride existing seams rather than missing prerequisites? Verify with file
citations: entity identity persistence; the 6C canonical-action and memory
seams; the 6D social-interaction, trust, and reciprocity records the 8C
enforcement path presumes. Output: the chain marked VERIFIED link-by-link
with citations, or a gap finding per broken link (which would reopen the
8B/8C contract assumptions at their STOPs — evidence decides).

## Close-out

The audit closes at a STOP when: W1's table and trend fits are pasted; W2's
finding rows (or per-surface "no blocking flaw" verdicts) are recorded with
citations; W3's clauses are committed and present in the 8B contract; W4's
pass is complete; W5's chain is cited — and **every finding is disposed**
(ratified decision / ledger row / protocol amendment / parked-work entry).
The close-out report records the disposition list, updates this file's
status to CLOSED, and updates the macro-roadmap's Stage 9 activation line
in the same commit series. Time-box: W1 wall-time is the long pole; W2/W4/W5
are one to two focused sessions. If any workstream exceeds its box, that is
reported at a STOP with options — never silently extended.
