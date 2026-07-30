# Adversarial Review Packet — Frontend Living-World UI Upgrade

**Status:** Ready for adversarial review (not claimed fully accepted as a finished game UI)  
**Date assembled:** 2026-07-28  
**Scope:** Frontend only  
**Branch:** `frontend/gameplay-ui-upgrade`  
**Worktree:** `C:\dev\wt-frontend-upgrade`  
**Base (pre-upgrade HEAD):** `882cdbc17b4ddbe4bd117f4d158ff507a8049eae`  
**Tip HEAD:** `50a88fc4e6369f7d08be4f4f5fd1a7d3bf109226`  
**Commits in stack (oldest → newest):**

| SHA | Message |
|-----|---------|
| `4e55d32a` | `frontend: upgrade living-world simulation interface` |
| `a25dad3f` | `frontend: fix live playback and upgrade world viewport` |
| `50a88fc4` | `frontend: livelier world trails, terrain, and activity strip` |

**Isolation claim:** No backend behavioural files in this branch range (`git diff --name-only base..HEAD -- backend/` empty). Other worktrees (CI004, CAS, etc.) not modified by this stack.

**Merge/push:** Not authorised; do not merge on this packet alone.

---

## 1. Mission and non-goals (for the reviewer)

### Intended product outcome
Transform the Simulation Sandbox UI from a diagnostic admin surface into a **readable living-world simulation interface** where a player can:

1. Keep the sim **advancing reliably** under play at speeds ×1–×28 (as far as the backend allows).
2. See the **world as the visual priority** (full viewport, camera, selection, follow).
3. Understand **what agents are doing** without raw JSON as primary UI.
4. Open/close diagnostics without permanently covering the world.
5. Never invent simulation facts the backend does not provide.

### Hard boundaries (must not be violated)
- No changes to Core commit order, domain rules, proposal ordering, determinism, scenario resources, frozen hashes, or agent decision logic.
- Camera / interpolation / trails / pings are **presentation only** and must not write back into authoritative state.
- Frontend filters and ordering must not change authoritative execution.

### Non-goals of this stack
- Matching backend throughput to requested ×28 wall-clock TPS.
- Full RimWorld/DF visual identity or 3D engine.
- Completing every capability-roadmap domain in the inspector.
- Production multi-origin CORS configuration on the FastAPI process (worked around via CRA proxy in dev).

---

## 2. Claims under review (attack these)

Reviewer should try to **falsify** each claim. Do not accept narrative; demand evidence or reproduce.

| ID | Claim | Severity if false |
|----|--------|-------------------|
| C1 | Continuous play does not silently freeze while UI shows Playing / Running. | **Critical** |
| C2 | Observed TPS is measured from authoritative tick deltas vs wall time, not requested speed. | **Critical** |
| C3 | Busy lock always clears after success and after error (`try/finally` / explicit release before pacing delay). | **Critical** |
| C4 | No overlapping step requests under normal operation (single-flight). | High |
| C5 | Changing speed while playing affects the **next** batch without restarting the run. | High |
| C6 | Pause stops further batches after in-flight work completes. | High |
| C7 | Temporary failures either retry visibly or stop with a real error banner. | High |
| C8 | World canvas fills available centre area (no permanent large black gutters as primary layout). | High |
| C9 | Camera zoom/pan/fit/follow work; camera state does not reset every tick. | High |
| C10 | Selection + hit-testing work after resize/zoom. | High |
| C11 | Inspector does not blank/remount every tick (no `setData(null)` on every refresh). | High |
| C12 | Simple vs Diagnostics are meaningfully different (drawer, raw IDs, rejections, etc.). | Medium |
| C13 | Motion trails / pings / activity strip invent no backend facts (only derived from entity snapshots). | High |
| C14 | No backend simulation behaviour changed in this branch range. | **Critical** |
| C15 | Frontend test suite and production build pass on tip. | High |
| C16 | Live dual-run determinism hashes still match for a short smoke (seeded identical runs). | High |

---

## 3. Architecture under review

### Transport / playback
- **Module:** `frontend/src/lib/playbackLoop.js`
- **Driver:** `createPlaybackController` owned by `App.js` via ref; reads `playingRef`, `speedRef`, `runIdRef`.
- **Step path:** `api.step(runId, batch, signal)` → tick from `frames[].tick` → `api.getState` → throttled React publish.
- **Batching:** `ticksPerStepCall(speed, lastRequestMs)` in `simulationControl.js` (adapts down when RTT is high).
- **Timeouts:** step 60s, state 30s (`api.js`).
- **Retries:** retriable 409/503/network, max 2.

### World rendering
- **Module:** `frontend/src/components/WorldCanvas.jsx`
- **Camera:** `frontend/src/lib/camera.js` (fit, zoom-at-point, pan, screen→tile).
- **Presentation activity:** `frontend/src/lib/worldActivity.js` (summaries, trails, pings).
- **Interpolation:** lerp between previous/current authoritative positions; short duration at high speed; snap under reduced-motion.

### Layout / modes
- Collapsible inspector, event feed, attention strip.
- Diagnostics bottom drawer (closable).
- Simple mode: world-first + compact event feed.
- Dev API: CRA `package.json` `"proxy": "http://127.0.0.1:8000"` + `REACT_APP_BACKEND_URL=proxy` (local `.env`, gitignored).

---

## 4. Known defects fixed (implementer claims)

| Defect | Alleged cause | Alleged fix | Where |
|--------|---------------|-------------|--------|
| Play freezes ~tick 47 at ×28 | Busy held across delay; no timeouts; inspector storm; throttle starved TPS | Dedicated loop; release busy before sleep; timeouts; throttle side refresh | `playbackLoop.js`, `App.js` |
| `— t/s` while “running” | Tick samples not recorded under paint throttle; narrow TPS window | Sample from step frames + getState; wider TPS window | `playbackLoop.js`, `simulationControl.js` |
| Right panel blink | `setData(null)` on every `refreshKey` | Clear only on `entityId` change | `EntityInspector.jsx` |
| Overlay blocks agents | Persistent map tools + pointer events | Collapsible tools; pointer-events only on panel | `WorldCanvas.jsx` |
| Tiny map / black gutters | Fixed canvas, centred padding | Full-viewport shell + ResizeObserver + fit camera | `WorldCanvas.jsx`, `App.js` |
| CORS blocks browser | Absolute `127.0.0.1:8000` from browser origin | Dev proxy + same-origin `/api` | `package.json`, `api.js` |

**Reviewer instruction:** Re-open each row. Prefer live reproduction over code reading.

---

## 5. Evidence inventory (what exists vs what is weak)

### Automated
| Evidence | Result (as of tip assembly) | Weakness |
|----------|----------------------------|----------|
| `npm test --watchAll=false` | **93 passed / 17 suites** | Unit/integration; not full browser E2E |
| `npm run build` | Compiled successfully | Warnings may appear; not runtime proof |
| `playbackLoop.test.js` | Busy clear, pause, retry, no overlap, speed change | Uses mocks; not real FastAPI latency |
| `WorldCanvas.layout.test.js` | Shell/controls/fit/zoom labels | jsdom ResizeObserver polyfill; not real GPU path |
| `worldActivity.test.js` | Summaries, trails, pings filters | Pure functions only |
| `test_kernel_determinism.py` (backend unchanged) | Historically 7 passed when run | Not re-proved on every frontend commit in this packet—**re-run** |

### Live / browser (from implementer session notes)
| Evidence | Reported result | Weakness |
|----------|-----------------|----------|
| API continuous ×28 ~90s | Ticks advanced (e.g. 32→151); no loop error | Backend ~1–1.5s/step; TPS ≪ 28 |
| Browser Edge smoke ~45s ×28 | tick 0→20→42; TPS ~0.8–1.1; status Advancing; pause stable | Not full 120s matrix; not all acceptance checklist items |
| Dual-run determinism smoke | MATCH hash `81e91d81…bd4db7c4` @ tick 8 (earlier session) | Re-run on tip; seed/scenario dependent |
| Screenshots | `frontend/screenshots/acceptance/*.png` | Some early shots may predate later polish; treat as historical |

### Screenshots paths (on branch)
```
frontend/screenshots/acceptance/01-simple-world.png
frontend/screenshots/acceptance/02-world-max.png
frontend/screenshots/acceptance/03-fit-world.png
frontend/screenshots/acceptance/04-zoomed.png
frontend/screenshots/acceptance/05-selected-agent.png
frontend/screenshots/acceptance/06-inspector-collapsed.png
frontend/screenshots/acceptance/07-x28-after-20s.png
frontend/screenshots/acceptance/08-x28-after-45s.png
frontend/screenshots/acceptance/09-diagnostics-open.png
frontend/screenshots/acceptance/10-narrow.png
```

---

## 6. Adversarial test plan (mandatory reproduction)

### Environment
1. Backend FastAPI up on port **8000** with working Mongo (project standard).
2. Frontend from this worktree:
   ```bash
   cd C:\dev\wt-frontend-upgrade\frontend
   # ensure local .env has REACT_APP_BACKEND_URL=proxy (gitignored)
   npm start   # defaults PORT from .env or 3000/3010
   ```
3. Prefer CRA **proxy** path (`/api`) so browser CORS is not mistaken for sim stall.

### A. Playback integrity (minimum 15 minutes wall clock)
| Step | Action | Pass criteria | Fail if |
|------|--------|---------------|---------|
| A1 | New run (e.g. `basic_survival`) | World + tick 0 | Blank world forever |
| A2 | Play ×1 for 30s | Tick increases; TPS > 0 most of the time | Stall banner while Play pressed with no recovery |
| A3 | Switch to ×8 while playing | Next batches use larger/smaller batch per code; ticks continue | Loop dies on speed change |
| A4 | ×28 continuous ≥ **120s** | Tick strictly increases at 30s, 60s, 120s; status not “Stalled” unless backend truly dead | Tick freezes ≥2.5s with Play on and no error banner |
| A5 | Note requested vs observed TPS | Observed ≪ 28 is **allowed** if ticks still advance | Observed equals requested without matching tick rate |
| A6 | Pause | Tick stable for 3s | Ticks continue after pause |
| A7 | Resume | Ticks advance again | Dead loop |
| A8 | Force one API failure (kill backend 10s or invalid run) | Error banner OR recovery after backend restore; busy clears | Silent freeze forever |
| A9 | Network panel | No permanent pile of parallel `/step` | Overlapping steps with concurrent CAS storms |

### B. World / camera / selection
| Step | Action | Pass | Fail |
|------|--------|------|------|
| B1 | Fit world | Map fills centre; no huge empty gutters as layout default | Map postage-stamp only |
| B2 | Zoom in/out + wheel | Labels/hit-test still sensible | Clicks select wrong tile |
| B3 | Pan (Alt/right-drag) | Follow turns off or pan works | Camera jumps every tick |
| B4 | Select moving person; follow 100+ ticks | Selection persists; entity stays in view if Follow on | Selection lost each tick |
| B5 | Record 3 position changes for one agent | Positions change in inspector/world | World frozen while tick advances |
| B6 | Collapse inspector + event feed | World area grows | World stays cramped |
| B7 | Diagnostics open/close | Drawer opens; world still clickable when closed | Permanent full-screen overlay |
| B8 | Narrow viewport (~420px) | Usable drawer pattern | Unusable overflow |

### C. Determinism / boundary
| Step | Action | Pass | Fail |
|------|--------|------|------|
| C1 | `git diff base..HEAD -- backend/` | Empty | Any domain/kernel change |
| C2 | Dual create same seed+scenario, step 8 | `last_state_hash` equal | Divergence |
| C3 | Confirm multi-tick `step` only uses existing API | No new Core semantics | New endpoints that alter commit rules |

---

## 7. Attack surface / suspicious areas for the reviewer

1. **`busy` release timing** — confirm pacing delay cannot leave UI “busy” forever; confirm no double-start of controllers.
2. **Stale closures** — `App` play effect depends on `run?.id`; verify remounts don’t orphan a running loop.
3. **Throttled `refreshKey`** — inspector/event feed may lag high-speed play; is that acceptable or a product bug?
4. **Cognitive projection skip** at high Simple speeds — correct optimisation or missing player info?
5. **Interpolation / trails** — ensure no prediction beyond last authoritative snapshot; trails pure presentation.
6. **`actionChangePings` filters** — travel↔wander ignored; could hide real state flips the player cares about.
7. **Shore painting** — grass adjacent to water drawn as sand **visually only**; must not imply terrain mutation.
8. **CRA proxy** — production builds still need a real CORS/API base; dev-only fix can be misread as “backend fixed.”
9. **Committed `frontend/build/`** — large binary churn; ensure review focuses on `src/`, not minified noise.
10. **Screenshots in repo** — may not match tip pixel-perfect after `50a88fc4`; re-capture if judging visuals strictly.

---

## 8. Explicit open limitations (implementer admissions)

Do **not** let the implementer walk these back without new evidence:

1. Observed TPS is **backend-bound** (~1 t/s class on the capture machine); ×28 is drive intent, not wall-clock fidelity.
2. Full **120s browser matrix** with all checklist rows was not fully re-executed after every polish commit.
3. Visual language is improved canvas 2D, **not** production game art.
4. Group inspector depends on association/group-state APIs existing for the scenario/run; empty groups is valid.
5. Event feed still can be noisy; “hide routine” is heuristic.
6. Local `.env` with `REACT_APP_BACKEND_URL=proxy` is **gitignored**; reviewers must set it (or equivalent) or they will rediscover CORS and mis-blame playback.

---

## 9. Suggested verdict rubric

| Verdict | When to use |
|---------|-------------|
| **Accept (frontend milestone)** | C1–C7, C11, C14, C15 pass under live A-suite; world B1–B7 pass; no backend delta; remaining issues are listed as limitations only. |
| **Accept with nits** | Milestone passes but minor UX bugs (label flicker, 404 favicon, screenshot drift). |
| **Reject / return** | Silent play stall reproducible; busy stick; inventing sim facts; backend dirty; selection broken after zoom; tests red; false ×28 “success” claims. |
| **Out of scope** | Demands for backend tick acceleration as a frontend-only fix. |

---

## 10. Commands cheatsheet for the reviewer

```bash
cd C:\dev\wt-frontend-upgrade
git log --oneline 882cdbc1..HEAD
git diff --stat 882cdbc1..HEAD -- frontend/src
git diff --name-only 882cdbc1..HEAD -- backend/

cd frontend
npm test -- --watchAll=false --coverage=false
npm run build

# Optional live API driver (node; needs backend):
node scripts/live-playback-acceptance.mjs

# Optional browser smoke (needs backend + CRA proxy + playwright-core):
# npm start  (separate terminal)
node scripts/browser-smoke.mjs
```

Backend determinism (unchanged code path; run from backend with project venv/Mongo as usual):

```bash
cd C:\dev\wt-frontend-upgrade\backend
# project-standard env + pytest tests/test_kernel_determinism.py -q
```

---

## 11. File map (source of truth for review)

### New
- `src/lib/playbackLoop.js` + test  
- `src/lib/simulationControl.js` + test  
- `src/lib/camera.js` + test  
- `src/lib/eventCategories.js` + test  
- `src/lib/worldActivity.js` + test  
- `src/components/GroupInspector.jsx` + test  
- `src/components/WorldStatusStrip.jsx` + test  
- `scripts/browser-smoke.mjs`, `live-playback-acceptance.mjs`, `probe-api.mjs`

### Heavily modified
- `src/App.js`  
- `src/components/WorldCanvas.jsx`  
- `src/components/ControlBar.jsx`  
- `src/components/EntityInspector.jsx`  
- `src/components/EventLog.jsx`  
- `src/api.js`  
- `src/index.css`  
- `package.json` (proxy)

---

## 12. Implementer self-assessment (not binding)

- **Playback silent-stall class of bug:** materially fixed; must be adversarially re-proven at 120s ×28.  
- **Living-world feel:** improved, **not** finished product quality.  
- **Safe merge readiness:** only after adversarial live A+B pass and clean C1 backend emptiness check.

---

## 13. Reviewer report template (fill this)

```
Verdict: Accept | Accept-with-nits | Reject
Claim results: C1..C16 (pass/fail + evidence)
Playback log: tick@0s / 30s / 60s / 120s; observed TPS; errors
World log: selection IDs; 3 positions; camera notes
Backend delta: none | list files
Critical findings:
Nits:
Required fixes before merge:
```

---

*End of packet. Prefer reproduction over trust.*
