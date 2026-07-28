/**
 * Browser smoke using system Edge via playwright-core channel.
 * Does not add a permanent package.json dependency.
 */
import { createRequire } from "module";
import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const shotDir = join(__dirname, "..", "screenshots", "acceptance");
mkdirSync(shotDir, { recursive: true });

const BASE = process.env.SMOKE_URL || "http://localhost:3010";
const API = (process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/+$/, "") + "/api";

async function ensurePlaywright() {
  try {
    const require = createRequire(import.meta.url);
    return require("playwright-core");
  } catch {
    console.log("Installing playwright-core temporarily...");
    const r = spawnSync("npm", ["install", "--no-save", "playwright-core@1.49.0"], {
      cwd: join(__dirname, ".."),
      shell: true,
      stdio: "inherit",
    });
    if (r.status !== 0) throw new Error("playwright-core install failed");
    const require = createRequire(import.meta.url);
    return require("playwright-core");
  }
}

async function main() {
  const { chromium } = await ensurePlaywright();
  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(String(err)));

  await page.goto(BASE, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1000);

  // Prefer Load Run path (API-created run) to avoid scenario-select flakiness
  if (await page.locator('[data-testid="new-run-modal"]').count()) {
    await page.locator('[data-testid="close-new-run-modal-btn"]').click().catch(() => {});
    await page.locator('[data-testid="cancel-new-run-btn"]').click().catch(() => {});
  }
  // Ensure a run exists (node-side absolute API; UI uses CRA proxy)
  const apiBase = "http://127.0.0.1:8000";
  const created = await fetch(`${apiBase}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seed: `browser-${Date.now()}`, scenario_id: "basic_survival" }),
  }).then((r) => r.json());
  console.log("precreated", created.id);

  await page.locator('[data-testid="load-run-btn"]').click();
  await page.waitForSelector('[data-testid="load-run-modal"]', { timeout: 15000 });
  await page.waitForSelector(`[data-testid="load-run-btn-${created.id}"]`, { timeout: 20000 });
  await page.locator(`[data-testid="load-run-btn-${created.id}"]`).click();

  await page.waitForSelector('[data-testid="world-canvas"]', { timeout: 30000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(shotDir, "01-simple-world.png"), fullPage: false });

  // Collapse feed and attention for max world
  if (await page.locator('[data-testid="toggle-event-feed"]').count()) {
    // ensure feed closed if open - click hide if present
    const t = page.locator('[data-testid="toggle-event-feed"]');
    const text = await t.textContent();
    if (text && /Hide/.test(text)) await t.click();
  }
  if (await page.locator('[data-testid="attention-collapse-toggle"]').count()) {
    const exp = await page.locator('[data-testid="attention-collapse-toggle"]').getAttribute("aria-expanded");
    if (exp === "true") await page.locator('[data-testid="attention-collapse-toggle"]').click();
  }
  await page.screenshot({ path: join(shotDir, "02-world-max.png"), fullPage: false });

  // Fit world
  if (await page.locator('[data-testid="fit-world"]').count()) {
    await page.locator('[data-testid="fit-world"]').click();
    await page.waitForTimeout(200);
    await page.screenshot({ path: join(shotDir, "03-fit-world.png"), fullPage: false });
  }

  // Zoom in
  if (await page.locator('[data-testid="zoom-in"]').count()) {
    await page.locator('[data-testid="zoom-in"]').click();
    await page.locator('[data-testid="zoom-in"]').click();
    await page.screenshot({ path: join(shotDir, "04-zoomed.png"), fullPage: false });
  }

  // Click canvas centre to select something
  const canvas = page.locator('[data-testid="world-canvas"]');
  const box = await canvas.boundingBox();
  if (box) {
    // scan a few points for an agent
    for (const [fx, fy] of [
      [0.4, 0.4],
      [0.5, 0.5],
      [0.35, 0.55],
      [0.6, 0.45],
      [0.45, 0.35],
    ]) {
      await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
      await page.waitForTimeout(150);
      if (await page.locator('[data-testid="entity-inspector-panel"]').count()) break;
    }
  }
  await page.screenshot({ path: join(shotDir, "05-selected-agent.png"), fullPage: false });

  // Collapse inspector
  if (await page.locator('[data-testid="toggle-side-panel"]').count()) {
    await page.locator('[data-testid="toggle-side-panel"]').click();
    await page.waitForTimeout(200);
    await page.screenshot({ path: join(shotDir, "06-inspector-collapsed.png"), fullPage: false });
    await page.locator('[data-testid="toggle-side-panel"]').click();
  }

  // Play ×28
  if (await page.locator('[data-testid="speed-preset-28"]').count()) {
    await page.locator('[data-testid="speed-preset-28"]').click();
  }
  if (await page.locator('[data-testid="play-pause-btn"]').count()) {
    await page.locator('[data-testid="play-pause-btn"]').click();
  }

  const tickEl = page.locator('[data-testid="tick-counter"]');
  const readTick = async () => {
    const t = await tickEl.textContent();
    const m = String(t).match(/(\d+)/);
    return m ? Number(m[1]) : null;
  };
  const tStart = await readTick();
  const startAt = Date.now();
  console.log("play start tick", tStart);

  // Packet-aligned partial browser window (full 120s API soak is live-playback-acceptance.mjs).
  // Default 60s continuous ×28; ACCEPTANCE_SHORT=1 shortens for debug only.
  const playMs = process.env.ACCEPTANCE_SHORT === "1" ? 20000 : 60000;
  await page.waitForTimeout(Math.floor(playMs / 2));
  const tMid = await readTick();
  const tpsMid = await page.locator('[data-testid="observed-tps"]').textContent();
  const statusMid = await page.locator('[data-testid="run-status-badge"]').textContent();
  await page.screenshot({ path: join(shotDir, "07-x28-after-20s.png"), fullPage: false });
  console.log("tMid", tMid, tpsMid, statusMid);

  await page.waitForTimeout(Math.ceil(playMs / 2));
  const tEnd = await readTick();
  const tpsEnd = await page.locator('[data-testid="observed-tps"]').textContent();
  const statusEnd = await page.locator('[data-testid="run-status-badge"]').textContent();
  await page.screenshot({ path: join(shotDir, "08-x28-after-45s.png"), fullPage: false });
  console.log("tEnd", tEnd, tpsEnd, statusEnd);

  // Pause — must stabilize ticks
  await page.locator('[data-testid="play-pause-btn"]').click();
  await page.waitForTimeout(2000);
  const tPause = await readTick();
  await page.waitForTimeout(2500);
  const tPause2 = await readTick();
  console.log("pause ticks", tPause, tPause2, "stable", tPause === tPause2);

  // Diagnostics
  if (await page.locator('[data-testid="view-mode-diagnostics"]').count()) {
    await page.locator('[data-testid="view-mode-diagnostics"]').click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: join(shotDir, "09-diagnostics-open.png"), fullPage: false });
    if (await page.locator('[data-testid="diagnostics-close"]').count()) {
      await page.locator('[data-testid="diagnostics-close"]').click();
    }
  }

  // Narrow viewport
  await page.setViewportSize({ width: 420, height: 800 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: join(shotDir, "10-narrow.png"), fullPage: false });

  await browser.close();

  const advanced = (tEnd || 0) > (tStart || 0) && (tEnd || 0) > (tMid || 0);
  const pauseStable = tPause != null && tPause === tPause2;
  const notStalled =
    !/stalled/i.test(String(statusMid || "")) && !/stalled/i.test(String(statusEnd || ""));
  const failures = [];
  if (!advanced) failures.push("ticks did not advance across mid and end checkpoints");
  if (!pauseStable) failures.push(`pause not stable (${tPause} vs ${tPause2})`);
  if (!notStalled) failures.push("status showed Stalled during healthy play");
  if (process.env.ACCEPTANCE_SHORT === "1") {
    failures.push("ACCEPTANCE_SHORT=1 is not full browser acceptance");
  }

  const report = {
    tStart,
    tMid,
    tEnd,
    advanced,
    pauseStable,
    notStalled,
    tpsMid,
    tpsEnd,
    statusMid,
    statusEnd,
    consoleErrors: consoleErrors.slice(0, 20),
    durationMs: Date.now() - startAt,
    failures,
    shotDir,
  };
  console.log("BROWSER_SMOKE_JSON", JSON.stringify(report, null, 2));
  if (failures.length) {
    console.error("BROWSER_SMOKE_FAIL", failures);
    process.exitCode = 3;
  } else {
    if (consoleErrors.length) console.warn("console noise", consoleErrors.length);
    console.log("BROWSER_SMOKE_PASS");
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
