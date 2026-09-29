// Verifies generated Mermaid against the real Mermaid bundle in headless Chromium:
// every case must parse and render, and every label must display literally.
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
// CommonJS resolution honours NODE_PATH, so a global Playwright install works too.
const { chromium } = require("playwright");
import fs from "node:fs";
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const browser = await chromium.launch();
const page = await browser.newPage();
page.on("dialog", (d) => { console.log("!!! DIALOG OPENED:", d.message()); d.dismiss(); });
await page.setContent("<!doctype html><html><body><div id=out></div></body></html>");
await page.addScriptTag({
  path: new URL("../../frontend/node_modules/mermaid/dist/mermaid.min.js", import.meta.url).pathname,
});
let failures = 0;
for (const [i, c] of cases.entries()) {
  const r = await page.evaluate(async ({ code, i }) => {
    mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
    try {
      await mermaid.parse(code);
      const { svg } = await mermaid.render(`g${i}`, code);
      const host = document.getElementById("out");
      host.innerHTML = svg;
      const text = host.textContent;
      return { ok: true, text, scripts: host.querySelectorAll("script").length };
    } catch (e) { return { ok: false, error: String(e.message || e) }; }
  }, { code: c.mermaid, i });
  if (!r.ok) { failures++; console.log(`FAIL ${c.name}: ${r.error.slice(0, 300)}`); continue; }
  const missing = c.labels.filter((l) => !r.text.includes(l));
  if (missing.length || r.scripts) { failures++; console.log(`FAIL ${c.name}: missing=${JSON.stringify(missing)} scripts=${r.scripts}`); }
  else console.log(`ok   ${c.name}: parsed, rendered, all ${c.labels.length} labels shown literally`);
}
await browser.close();
process.exit(failures ? 1 : 0);
