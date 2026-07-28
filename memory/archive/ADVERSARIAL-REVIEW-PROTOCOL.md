# Stage-End Adversarial Review Protocol

Status: ACTIVE — standing doctrine, user-ruled 2026-07-20.
Scope: every stage/leg close-out, starting with Stage 8B Leg 1.
CLAUDE.md carries the index entry; this document is the authority.

## 1. Targets are claims, not code

Review inputs: the confirmed contract with its decision log, the full
branch diff, the persisted evidence files, and the draft close-out claims
as a bare list. The reviewer's job is to falsify each claim, with specific
attention to:

- undeclared scope reach (a domain affecting behaviour outside its contract)
- evidence–claim mismatches (numbers or facts the evidence files do not
  actually support)
- any contract language amended or classified during the stage.

## 2. Blind first pass

The reviewer does not receive the implementing agent's justification
narrative or self-assessment before its first pass — claims arrive as bare
assertions. After the first pass, the implementing agent may rebut each
finding, and the reviewer holds or withdraws each one.

Builder-seeded concerns: the implementing agent may submit its own suspected
flaws, but only after the blind first pass completes — never before or with
the initial claims. Seeded items are tagged builder-seeded in the findings
ledger. A review whose findings are entirely builder-seeded is insufficient:
the reviewer must either produce at least one independent finding or state
explicitly, per claim, that no independent flaw was found.

## 3. Independence

The reviewer model must differ from the implementing model, and at least
one non-Anthropic model participates (existing Codex / Zen MCP pattern).
Record the independence level honestly in the report.

## 4. Findings ledger

Every finding gets exactly one disposition:

- FIX — change made, referenced in the ledger entry
- ACCEPT — reason recorded
- DISPUTE — unresolved; escalates to the user at the close-out STOP

No finding is dropped silently. The ledger ships inside the close-out
report.

## 5. Proportionality cap

Scope is this stage's diff plus this stage's judgment calls only — no
re-auditing prior stages. A suspected prior-stage issue is filed as a
DISPUTE for the user, not an expanded review.
