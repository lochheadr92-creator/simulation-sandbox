import { chromium } from "playwright-core";

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage();
page.on("console", (m) => console.log("CONSOLE", m.type(), m.text()));
page.on("requestfailed", (r) => console.log("REQFAIL", r.url(), r.failure()?.errorText));
page.on("response", (r) => {
  if (r.url().includes("/api/")) console.log("RESP", r.status(), r.url());
});
await page.goto("http://localhost:3010", { waitUntil: "networkidle", timeout: 60000 });
const apiTest = await page.evaluate(async () => {
  try {
    const r = await fetch("/api/scenarios");
    return { status: r.status, ok: r.ok, body: (await r.text()).slice(0, 180) };
  } catch (e) {
    return { error: String(e) };
  }
});
console.log("API_FROM_BROWSER", JSON.stringify(apiTest));
const hint = await page.locator('[data-testid="api-base-hint"]').textContent().catch(() => null);
console.log("API_HINT", hint);
await page.screenshot({ path: "screenshots/acceptance/debug-modal.png" });
await browser.close();
