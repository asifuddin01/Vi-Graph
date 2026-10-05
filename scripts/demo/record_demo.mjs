// Records the demo video and takes the screenshots in one scripted run of the app.
//
//   NODE_PATH="$(npm root -g)" node scripts/demo/record_demo.mjs IMAGES_DIR OUT_DIR
//   scripts/demo/encode.sh OUT_DIR          # frames → vigraph-demo.mp4 + vigraph-demo.gif
//
// Needs the frontend on :3000 (APP_URL) and the backend on :8000, normally replay_server.py.
// The video is Chromium's screencast (sharp text, unlike Playwright's built-in recorder),
// written as JPEG frames plus an ffmpeg concat list. A drawn cursor and captions are overlaid
// for the video only: screenshots hide them, and frames taken while they are hidden are left
// out. The model's wait is shortened to WAIT_SHOWN_S seconds in the video; the caption that
// follows gives the real time.
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
// CommonJS resolution honours NODE_PATH, so a global Playwright install works too.
const { chromium } = require("playwright");

const [imagesDir, outDir] = process.argv.slice(2);
if (!imagesDir || !outDir) {
  console.error("usage: record_demo.mjs IMAGES_DIR OUT_DIR");
  process.exit(2);
}
const APP = process.env.APP_URL ?? "http://localhost:3000";
const VIEWPORT = { width: 1600, height: 1000 };
const WAIT_SHOWN_S = 2.5;
const MAIN = {
  image: "test-000381.png",
  node: "Merge Replicates",
  question: "What feeds into Merge Replicates?",
};
const EXTRA = [
  { name: "ml-pipeline", image: "test-000181.png" },
  { name: "system-architecture", image: "test-000329.png" },
];

const marks = [];
const mark = (kind) => marks.push({ kind, t: Date.now() / 1000 });

// ---- overlays (video only) --------------------------------------------------------------
function installOverlays() {
  const install = () => {
    const cursor = document.createElement("div");
    Object.assign(cursor.style, {
      position: "fixed", left: "-50px", top: "-50px", width: "22px", height: "22px",
      margin: "-11px 0 0 -11px", borderRadius: "50%", background: "rgba(14,165,233,.30)",
      border: "2px solid rgba(2,132,199,.95)", zIndex: 2147483647, pointerEvents: "none",
      transition: "transform .08s",
    });
    const caption = document.createElement("div");
    Object.assign(caption.style, {
      position: "fixed", left: "50%", bottom: "28px", transform: "translateX(-50%)",
      width: "max-content", maxWidth: "84vw", padding: "12px 24px", borderRadius: "12px",
      display: "none",
      background: "rgba(24,24,27,.92)", color: "#fff", zIndex: 2147483646,
      font: "600 21px/1.35 ui-sans-serif, system-ui, sans-serif", textAlign: "center",
      boxShadow: "0 8px 30px rgba(0,0,0,.25)", pointerEvents: "none",
    });
    document.body.append(cursor, caption);
    addEventListener("mousemove", (e) => {
      cursor.style.left = `${e.clientX}px`;
      cursor.style.top = `${e.clientY}px`;
    }, true);
    addEventListener("mousedown", () => (cursor.style.transform = "scale(.7)"), true);
    addEventListener("mouseup", () => (cursor.style.transform = "scale(1)"), true);
    window.__caption = (text) => {
      caption.textContent = text ?? "";
      caption.style.display = text ? "block" : "none";
    };
    window.__overlays = (visible) => {
      cursor.style.visibility = caption.style.visibility = visible ? "visible" : "hidden";
    };
    window.__repaint = () => {
      caption.style.opacity = "0.99";
      requestAnimationFrame(() => requestAnimationFrame(() => (caption.style.opacity = "1")));
    };
  };
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", install);
  else install();
}

// ---- helpers ----------------------------------------------------------------------------
async function newPage(browser) {
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 2,
    colorScheme: "light",
  });
  await context.addInitScript(installOverlays);
  const page = await context.newPage();
  await page.goto(APP);
  await page.getByText(/VLM: /).waitFor();
  return { context, page };
}

const caption = (page, text) => page.evaluate((t) => window.__caption(t), text);

async function moveTo(page, locator, { dx = 0, dy = 0, steps = 25 } = {}) {
  const box = await locator.boundingBox();
  await page.mouse.move(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy, { steps });
  await page.waitForTimeout(150);
}

async function clickOn(page, locator, options) {
  await moveTo(page, locator, options);
  await page.mouse.down();
  await page.waitForTimeout(90);
  await page.mouse.up();
}

async function scrollTo(page, top) {
  await page.evaluate((y) => window.scrollTo({ top: y, behavior: "smooth" }), top);
  await page.waitForTimeout(1100);
}

// The screencast only sends a frame when the page repaints: let the current state reach the
// video before hiding the overlays, and repaint after the window so the video resumes on a
// frame that shows them again.
async function shot(page, name, options = {}) {
  await page.waitForTimeout(400);
  mark("shot-start");
  await page.evaluate(() => window.__overlays(false));
  await page.waitForTimeout(100);
  await page.screenshot({ path: path.join(outDir, `${name}.png`), ...options });
  await page.evaluate(() => window.__overlays(true));
  await page.waitForTimeout(100);
  mark("shot-end");
  await page.evaluate(() => window.__repaint());
  await page.waitForTimeout(200);
}

async function analyze(page, image, { onWait, onDone } = {}) {
  const analyzeButton = page.getByRole("button", { name: "Analyze", exact: true });
  await page.getByTestId("file-input").setInputFiles(path.join(imagesDir, image));
  await page.waitForTimeout(1200);
  await clickOn(page, analyzeButton);
  mark("wait-start");
  if (onWait) await onWait();
  await page.getByTestId("result-status").waitFor({ timeout: 300_000 });
  mark("wait-end");
  if (onDone) await onDone();
  await page.getByTestId("graph-editor").locator(".react-flow__node").first().waitFor();
  await page.waitForTimeout(1200); // ELK layout + fit view
}

async function startScreencast(context, page, dir) {
  fs.mkdirSync(dir, { recursive: true });
  const cdp = await context.newCDPSession(page);
  const frames = [];
  cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    const file = `f${String(frames.length).padStart(5, "0")}.jpg`;
    fs.writeFileSync(path.join(dir, file), Buffer.from(data, "base64"));
    frames.push({ file, t: metadata.timestamp });
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
  });
  await cdp.send("Page.startScreencast", {
    format: "jpeg",
    quality: 88,
    maxWidth: 1920,
    maxHeight: 1200,
  });
  return { frames, stop: () => cdp.send("Page.stopScreencast") };
}

// ffmpeg concat list: each frame lasts until the next one; frames taken while a screenshot
// hid the overlays are dropped; the model wait is scaled down to WAIT_SHOWN_S.
function concatList(frames, endHold = 2.5) {
  const windows = (kind) =>
    marks
      .filter((m) => m.kind === `${kind}-start`)
      .map((m) => [m.t, marks.find((e) => e.kind === `${kind}-end` && e.t >= m.t).t]);
  const shots = windows("shot");
  const [wait] = windows("wait");
  const scale = WAIT_SHOWN_S / (wait[1] - wait[0]);
  const kept = frames.filter((f) => !shots.some(([a, b]) => f.t >= a && f.t <= b));
  const lines = [];
  kept.forEach((frame, i) => {
    const end = i + 1 < kept.length ? kept[i + 1].t : frame.t + endHold;
    const inWait = Math.max(0, Math.min(end, wait[1]) - Math.max(frame.t, wait[0]));
    const duration = end - frame.t - inWait + inWait * scale;
    lines.push(`file '${frame.file}'`, `duration ${duration.toFixed(4)}`);
  });
  lines.push(`file '${kept.at(-1).file}'`);
  return lines.join("\n") + "\n";
}

// ---- the walkthrough (video + screenshots) ----------------------------------------------
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
{
  const { context, page } = await newPage(browser);
  const framesDir = path.join(outDir, "frames");
  fs.rmSync(framesDir, { recursive: true, force: true });
  await page.mouse.move(820, 560);
  const recording = await startScreencast(context, page, framesDir);
  const pause = (ms) => page.waitForTimeout(ms);

  await caption(page, "Vi-Graph turns a diagram image into an editable, queryable graph");
  await pause(3000);
  await caption(page, "1 · Upload a diagram (PNG, JPEG or WebP)");
  await moveTo(page, page.getByText("Drop a diagram here, or click to choose"));
  await pause(500);
  await analyze(page, MAIN.image, {
    onWait: () => caption(page, "2 · The fine-tuned VLM (Qwen3-VL-2B + QLoRA) reads the diagram …"),
    onDone: async () => {
      const header = await page.getByText(/ · \d+ ms$/).textContent();
      const seconds = (Number(header.match(/(\d+) ms$/)[1]) / 1000).toFixed(1);
      const nodes = await page.locator("dt:text-is('Nodes') + dd").textContent();
      const edges = await page.locator("dt:text-is('Edges') + dd").textContent();
      await caption(
        page,
        `3 · Valid on the first try: ${nodes} nodes, ${edges} edges ` +
          `(${seconds} s on an RTX 4080 SUPER, sped up here)`,
      );
    },
  });
  await shot(page, "vigraph-analyze");
  await pause(4000);

  await caption(page, "4 · Edit the graph: select a node to inspect, rename or retype it");
  const editor = page.getByTestId("graph-editor");
  await clickOn(page, editor.locator(".react-flow__node", { hasText: MAIN.node }));
  await pause(3000);
  await clickOn(page, editor.locator(".react-flow__pane"), { dx: -250, dy: -200 });
  await pause(600);

  await scrollTo(page, 260);
  await caption(page, "5 · Ask questions, answered from the reconstructed graph");
  const input = page.getByRole("textbox", { name: "Question" });
  await clickOn(page, input);
  await input.pressSequentially(MAIN.question, { delay: 55 });
  await pause(300);
  await clickOn(page, page.getByRole("button", { name: "Ask", exact: true }));
  await page.getByTestId("qa-answer").first().waitFor();
  await pause(800);
  await caption(page, "The nodes an answer is based on light up in the graph");
  await pause(2500);
  await shot(page, "vigraph-qa");
  await pause(1500);

  await caption(page, "Quick questions: explain, find parallel branches, analyze topology");
  await clickOn(page, page.getByRole("button", { name: "Find branches", exact: true }));
  await page.getByTestId("qa-answer").nth(1).waitFor();
  await pause(3500);

  await caption(page, "6 · Mermaid code, plus export to SVG, PNG, PDF and JSON");
  const mermaidTop = await page.getByTestId("mermaid-diagram").evaluate(
    (el) => el.getBoundingClientRect().top + window.scrollY - 120,
  );
  await scrollTo(page, mermaidTop);
  await pause(3000);

  await caption(page, "Every raw model output, retry and repair is logged");
  const attempt = page.locator("summary", { hasText: "Attempt 1" });
  await attempt.evaluate((el) => window.scrollTo({
    top: el.getBoundingClientRect().top + window.scrollY - 200, behavior: "smooth",
  }));
  await pause(1200);
  await clickOn(page, attempt);
  await pause(3500);
  await shot(page, "vigraph-full-page", { fullPage: true });

  await scrollTo(page, 0);
  await caption(page, "Model output replayed from the recorded evaluation run · github.com/asifuddin01/Vi-Graph");
  await pause(3500);
  await recording.stop();
  fs.writeFileSync(path.join(framesDir, "frames.txt"), concatList(recording.frames));
  console.log(`video: ${recording.frames.length} frames`);
  await context.close();
}

// ---- more screenshots: other diagram types and themes -----------------------------------
for (const extra of EXTRA) {
  const { context, page } = await newPage(browser);
  await analyze(page, extra.image);
  await shot(page, `vigraph-${extra.name}`);
  console.log(`screenshot: ${extra.name}`);
  await context.close();
}
await browser.close();
