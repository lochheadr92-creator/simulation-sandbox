# Adversarial Review Report — Frontend Living-World UI Upgrade

**Review date:** 2026-07-28  
**Verdict:** **Reject / return before merge**  
**Branch:** `frontend/gameplay-ui-upgrade`  
**Base:** `882cdbc17b4ddbe4bd117f4d158ff507a8049eae`  
**Reviewed HEAD:** `50a88fc4e6369f7d08be4f4f5fd1a7d3bf109226`  
**Reviewer:** Codex (GPT-5, in-process review; no independent second reviewer)  
**Scope:** Frontend stack and its supplied acceptance evidence. No implementation files were modified.

## Result

Steady-state playback is materially improved: more than 15 minutes of browser-driven play completed without a silent freeze, observed TPS remained distinct from requested speed, camera controls worked, selection persisted, the inspector stayed mounted, the frontend tests/build passed, the backend diff is empty, and dual-run determinism matched.

The stack is not merge-ready because stop/restart is not single-flight, pause can finalize against stale authoritative state, and two presentation paths display changes that did not occur. The default/resize layout also reproduces the packet's prohibited large-gutter condition. The supplied acceptance scripts can print `PASS` without executing or enforcing the packet's mandatory criteria.

## Findings, ranked

### 1. Critical — stop/restart can overlap authoritative step requests and race pause finalization

**Verdict:** C4 fails and C6 fails as a complete user-visible pause contract.

**Why:** `stop()` aborts the client request, immediately sets the shared `busy` flag to false, and does not await `loopPromise` or the in-flight step (`src/lib/playbackLoop.js:329-351`). A subsequent `start()` can therefore issue another step while the server is still completing the first one. `App` also calls `/pause` immediately after `stop()` (`src/App.js:269-283`), while a late frame commit sets run status back to `running` (`backend/core/storage/frame_transaction.py:595-610`).

Confirmed evidence:

- An actual-module deferred-step probe produced `calls=2`, `inFlight=2`, `maxInFlight=2` across stop/start.
- Live pause #1 showed UI `Tick 287 / Paused`, but authoritative state settled at tick 293 with status `running`; it then remained stable at 293.
- Later pauses repeatedly left the UI one tick behind the final authoritative state (for example UI 1033 vs backend 1034).
- The bug is caused by frontend lifecycle ordering; `git diff base..HEAD -- backend/` is empty.

**Alternative:** Make controller shutdown await the current loop/request settlement. Keep `busy` owned by the request's `finally`, serialize stop/start generations, post `/pause` only after the in-flight step has settled, and fetch/publish the final state before reporting `Paused`. Add a regression test whose step promise ignores abort long enough to prove `maxInFlight === 1` across pause/resume.

### 2. High — unchanged injured/resource-carrying entities emit false change effects every tick

**Verdict:** C13 fails.

**Why:** `WorldCanvas` passes `prevEntitiesRef` into `acceptedChangeEffects`, then stores only `id`, `type`, `alive`, `position`, and `action` for the next comparison (`src/components/WorldCanvas.jsx:524-537`). The detector also compares `injury`, `food_inventory`, and `inventory` (`src/lib/worldOverlay.js:79-98`). Those missing prior fields are treated as false/zero, so an unchanged injured or resource-carrying entity is announced as newly injured/resource-gaining on every published tick.

Actual-module probe for an unchanged entity returned:

```json
[{"type":"injury","id":"p","at":{"x":1,"y":1}},{"type":"resource","id":"p","at":{"x":1,"y":1}}]
```

**Alternative:** Use one normalized comparison snapshot that retains every field the detector reads, or pass complete immutable entity snapshots. Add an integration regression asserting that two identical successive snapshots emit no effects.

### 3. High — stationary entities repeatedly animate from their previous tile

**Verdict:** C13 fails independently of Finding 2.

**Why:** On a real movement, `prevPosRef` records the old tile. On later ticks with an unchanged target position, that old value is retained, but `interpStartRef` is reset on every state update (`src/components/WorldCanvas.jsx:479-541`). `interpFor` therefore restarts the old-to-current lerp every tick (`src/components/WorldCanvas.jsx:643-654`).

Live evidence at tick 1035 showed stationary `person-005`, authoritatively fixed at `(10,2)`, drawn partway from the prior tile immediately after publish and only settling onto `(10,2)` about 250 ms later. The false movement repeated on unchanged state updates.

**Alternative:** Start interpolation only when coordinates actually change. Once settled—or when the next snapshot is unchanged—advance the interpolation baseline to the current target. Add a repeated-identical-state canvas test.

### 4. High — default and resized camera layouts retain the prohibited large gutters

**Verdict:** C8 fails; B6 is only partially satisfied.

**Why:** The canvas element grows, but the map remains a contained square. In the maximized desktop layout, the measured canvas was approximately `1279 × 594`; fit zoom was `0.90`, so the 640-pixel world occupied about 576 horizontal pixels and left about 703 pixels (55% of the canvas width) as dark gutter. On viewport/panel resize, `ResizeObserver` updates the canvas dimensions but refits only before `fittedOnceRef` is set (`src/components/WorldCanvas.jsx:553-577`). After fitting at 420px and restoring desktop width, the map stayed at zoom `0.63`, only about 403px wide, and remained anchored to the old viewport geometry.

**Alternative:** Define a resize policy that preserves the world-space focal point and recenters/clamps offsets. When the user has not manually moved the camera, refit on container changes. For the default world-first presentation, use a cover/default zoom or a non-empty terrain/backdrop treatment so the map is not a postage stamp inside a mostly black canvas.

### 5. High — supplied acceptance scripts can report `PASS` without satisfying the packet

**Verdict:** The script output is not sufficient merge evidence.

**Why:** `scripts/live-playback-acceptance.mjs` runs ×1 for 15 seconds and ×28 for 90 seconds, below the packet's 30/120-second requirements (`scripts/live-playback-acceptance.mjs:124-132`). Its TPS calculation has no wider-window fallback (`:24-31`), and the live run advanced from tick 45 to 170 while reporting `tps: 0` at several checkpoints and at the end. It still printed `ACCEPTANCE_PASS`; its `avgRtt` field is actually the longest RTT (`:108-120`), and the final pass predicate does not include all reported checks (`:189-197`). The browser smoke runs only 45 seconds and prints pass based on advancement alone, not pause stability or console errors (`scripts/browser-smoke.mjs:146-167`, `:186-203`).

**Alternative:** Make the scripts import the production batching/TPS helpers, execute the packet's exact durations, and fail on every mandatory criterion. Rename partial probes so they cannot be mistaken for acceptance, and emit structured timestamps/ticks/TPS/errors for each checkpoint.

## Claim results

| Claim | Result | Evidence |
|---|---|---|
| C1 | **PASS** | Browser playback exceeded 15 minutes total. The 12-minute uninterrupted ×28 soak advanced tick 320 → 1026 with no error banner. |
| C2 | **PASS** | At requested ×28, UI showed observed throughput around 0.7–1.2 t/s while authoritative ticks advanced. Sampler uses tick/time deltas. |
| C3 | **PASS (narrowly)** | Success/error busy release is protected by `finally`; focused tests passed. The unsafe explicit release in `stop()` is Finding 1/C4. |
| C4 | **FAIL** | Actual-module stop/start probe reached two simultaneous in-flight step calls. |
| C5 | **PASS** | Live ×1 → ×8 → ×28 changes continued without restarting the run; requested control updated in place. |
| C6 | **FAIL** | No continuing batch stream was observed while paused, but pause did not await/finalize the in-flight step; UI/backend tick and status diverged. |
| C7 | **PASS, limited evidence** | Unit tests proved bounded retry and visible stop/error wiring. A live backend-kill injection was not performed against the shared service. |
| C8 | **FAIL** | Measured 55% horizontal dark gutter even in maximized fit; resize retained stale camera geometry. |
| C9 | **PASS** | Fit, zoom, Alt-drag pan, center, and follow worked; camera stayed at `0.90×` through hundreds of ticks. |
| C10 | **PASS** | After a 420×800 resize and fit, selection was cleared then `person-005` was correctly reselected at the computed tile; zoomed selection also worked. |
| C11 | **PASS** | Inspector regression test passed; live play retained one inspector panel with no loading/error remount. |
| C12 | **PASS** | Simple mode showed summaries; Diagnostics opened a closable drawer plus raw IDs, raw fields, rejections, and diagnostics tabs. |
| C13 | **FAIL** | False repeated injury/resource effects and false stationary movement were both reproduced. |
| C14 | **PASS** | `git diff --name-only 882cdbc1..HEAD -- backend/` returned empty. |
| C15 | **PASS with warnings** | 93 tests / 17 suites passed; production build succeeded with one hook-dependency warning. Layout tests also emitted React `act(...)` warnings. |
| C16 | **PASS** | Dual-run smoke matched `81e91d81acba3168a4580894daf1d81c072dee043c07af3dbc976951bd4db7c4` at tick 8; kernel determinism tests were 7/7. |

## Playback log

Browser run: `run-dbfde30bb1f2`, seed `adversarial-frontend-20260728`, scenario `basic_survival`.

- ×1: tick 0 → 28 in 30 seconds; observed `1 t/s`; no error.
- ×8 live switch: tick continued to 63 after 20 seconds; observed `1.1 t/s`; no restart/error.
- ×28 mandatory window: tick 77 / 118 / 188 / 238 / 279 at 0 / 30 / 60 / 90 / 120 seconds; observed TPS 0.8–1.2.
- ×28 extended soak: tick 320 → 1026 over 720 seconds; checkpoints remained `Advancing`, TPS 0.7–1.0, no error, selection retained.
- Pause: UI stabilized for more than 3 seconds, but final authoritative tick/status did not reliably match the UI (Finding 1).
- Resume: recovered and advanced again without remounting the controller.

## World log

- Selected/followed: `person-005` (`Traveller 6`); selection persisted through more than 1,000 ticks.
- Authoritative position history for `person-004`: tick 1 `(15,3)`, tick 2 `(16,3)`, tick 3 `(16,4)`, tick 4 `(16,5)`, tick 5 `(16,6)`.
- Camera: fit `0.90×`; zoomed to `1.19×`; Alt-drag panned and disabled Follow; center restored the selected entity.
- Narrow viewport: `420 × 800`, no horizontal document overflow, diagnostics drawer `420 × 176`, world area remained available, and post-resize hit-testing worked after Fit.
- Diagnostics opened/closed cleanly; the world canvas remained present after closing.

## Verification

- `npm test -- --watchAll=false --coverage=false --runInBand` — **passed**, 93 tests / 17 suites; React `act(...)` warnings in `App.layout.test.js`.
- `npm run build` — **passed with warning** (`WorldStatusStrip.jsx:17` unnecessary hook dependency). The generated sourcemap rewrite was restored; no implementation diff remains.
- `C:\Users\RJLoc\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests\test_kernel_determinism.py -q` — **passed**, 7 tests.
- `node scripts/live-playback-acceptance.mjs` — exited 0 and dual-run hash matched, but its `ACCEPTANCE_PASS` is not valid packet acceptance for the reasons in Finding 5.
- Browser matrix — completed against target CRA server on port 3010 and live FastAPI on port 8000.
- Actual-module adversarial probes — reproduced stop/start overlap and unchanged-entity false effects.

## Risks and limits

- Live failure injection by killing the shared backend was not performed. C7 therefore has automated/code evidence, not the packet's destructive A8 variant.
- The running FastAPI command line did not expose its working directory, so live-service checkout provenance could not be proven from process metadata. The target worktree's backend determinism test was run separately, and this branch range has no backend changes.
- This review did not collect a GPU trace or test a second browser engine.
- Live verification created five Mongo test runs (`run-f884ccb7687d`, `run-a3807bb3afbe`, `run-62b472fb66af`, `run-9f58aafc9e08`, `run-dbfde30bb1f2`). They were not deleted.

## Required fixes before merge

1. Serialize controller stop/start and finalize pause only after the in-flight request settles; refresh the final authoritative state.
2. Correct the previous-entity snapshot used by `acceptedChangeEffects` and add an unchanged-state integration test.
3. Start interpolation only on real position changes and settle its baseline.
4. Fix default/resize camera framing so layout growth does not create a postage-stamp map or stale offsets.
5. Make the acceptance scripts enforce the packet's actual durations and all mandatory pass criteria.

## Git state at review completion

- Branch: `frontend/gameplay-ui-upgrade`
- HEAD: `50a88fc4e6369f7d08be4f4f5fd1a7d3bf109226`
- Implementation changes made by reviewer: none
- Review artifact added: `frontend/ADVERSARIAL-REVIEW-REPORT.md`
- Pre-existing untracked paths preserved: `.venv/`, `frontend/ADVERSARIAL-REVIEW-PACKET.md`
- Commit/push/merge: not performed
