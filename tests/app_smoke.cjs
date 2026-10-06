// Uses the built app the way a person does, in a headless Chromium driven
// over the DevTools protocol, and prints a JSON report. Run by
// tests/test_app_smoke.py, which starts the browser and a static server.
//
// Usage: node app_smoke.cjs <devtools-port> <app-url> <peivaste-csv> <peivaste-url> <version>
//
// The engine's Peivaste download is answered from the local file, so the
// run never depends on the network. Uncaught errors, console errors and
// failed loads anywhere in the page or its worker are reported as problems.

"use strict";

const fs = require("fs");

const [port, appUrl, peivastePath, peivasteUrl, version] = process.argv.slice(2);

function report(value) {
  console.log(JSON.stringify(value));
  process.exit(0);
}

if (typeof WebSocket !== "function") report({ skip: "Node 22 or newer is needed (global WebSocket)" });

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    const pending = new Map();
    const listeners = [];
    let next = 0;
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id !== undefined && pending.has(msg.id)) {
        const call = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) call.reject(new Error(msg.error.message));
        else call.resolve(msg.result);
      } else {
        listeners.forEach((listener) => listener(msg));
      }
    };
    ws.onerror = () => reject(new Error("could not connect to " + url));
    ws.onopen = () =>
      resolve({
        send(method, params, sessionId) {
          const id = ++next;
          ws.send(JSON.stringify({ id, method, params: params || {}, sessionId }));
          return new Promise((res, rej) => pending.set(id, { resolve: res, reject: rej }));
        },
        on(listener) {
          listeners.push(listener);
        },
        close() {
          ws.close();
        },
      });
  });
}

// Installed once in the page. Downloads are captured instead of saved.
function HELPERS() {
  if (window.__smoke) return true;
  const blobs = [];
  const createObjectURL = URL.createObjectURL.bind(URL);
  URL.createObjectURL = (blob) => {
    blobs.push(blob);
    return createObjectURL(blob);
  };
  const anchorClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () {
    if (!this.hasAttribute("download")) anchorClick.call(this);
  };
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const $ = (id) => document.getElementById(id);
  const errorsIn = (el) =>
    Array.from(el.querySelectorAll(".feature-error, .engine-gate.is-error"))
      .map((e) => e.textContent.trim())
      .filter(Boolean);
  async function waitFor(label, check, ms, scope) {
    const until = Date.now() + ms;
    for (;;) {
      if (scope && errorsIn(scope).length) throw new Error("while waiting for " + label + ": " + errorsIn(scope)[0]);
      let value = null;
      try {
        value = check();
      } catch (e) {
        value = null;
      }
      if (value) return value;
      if (Date.now() > until) throw new Error("timed out waiting for " + label);
      await sleep(100);
    }
  }
  function clean(el, label) {
    const errors = errorsIn(el);
    if (errors.length) throw new Error(label + " shows an error: " + errors[0]);
  }
  function view(name) {
    location.hash = name;
    return waitFor("the " + name + " view", () => document.querySelector('.view[data-view-panel="' + name + '"].view--active'), 10000);
  }
  async function download(trigger, label) {
    const before = blobs.length;
    trigger();
    await waitFor(label + " download", () => blobs.length > before, 300000);
    return blobs[blobs.length - 1].text();
  }
  function rows(tbodyId) {
    return $(tbodyId).querySelectorAll("tr").length;
  }
  window.__smoke = { $, waitFor, clean, view, download, rows };
  return true;
}

// Each step runs in the page and returns a short description of what it saw.
const STEPS = [
  [
    "landing page",
    async (version) => {
      const S = window.__smoke;
      await S.waitFor("the landing page and version badge", () => !document.body.classList.contains("show-app") && S.$("version-badge").textContent.includes(version), 10000);
      if (!Array.from(document.querySelectorAll("h2")).some((h) => /What you can do here/.test(h.textContent))) throw new Error("no 'What you can do here' section");
      return S.$("version-badge").textContent.trim();
    },
  ],
  [
    "calculator (alloys)",
    async () => {
      const S = window.__smoke;
      const view = await S.view("calc");
      document.querySelector('.mode-btn[data-mode="alloy"]').click();
      S.$("formula-input").value = "CoCrFeMnNi";
      S.$("parse-formula").click();
      S.$("calculate").click();
      await S.waitFor("the Cantor descriptors", () => /Mixing entropy/.test(S.$("results").textContent) && /13\.38/.test(S.$("results").textContent), 30000, view);
      await S.waitFor("the phase-rule verdicts", () => S.$("rule-predictions").textContent.trim().length > 20, 30000, view);
      await S.waitFor("the Omega pair-table check", () => /Ω/.test(S.$("omega-sensitivity").textContent), 30000, view);
      await S.waitFor("density and cost", () => /Density/.test(S.$("predict-tier-a").textContent) && /USD\/kg/.test(S.$("predict-tier-a").textContent), 30000, view);
      S.clean(view, "the calculator");
      return S.$("results").querySelectorAll(".result-card").length + " descriptor cards for CoCrFeMnNi";
    },
  ],
  [
    "calculator (oxides)",
    async () => {
      const S = window.__smoke;
      await S.view("calc");
      document.querySelector('.mode-btn[data-mode="oxide"]').click();
      const example = S.$("oxide-example");
      example.value = Array.from(example.options).find((o) => o.value).value;
      example.dispatchEvent(new Event("change", { bubbles: true }));
      S.$("oxide-calculate").click();
      await S.waitFor("the oxide descriptors", () => S.$("oxide-results").textContent.trim().length > 40, 30000, S.$("oxide-panel"));
      S.clean(S.$("oxide-panel"), "the oxide calculator");
      return "example " + S.$("oxide-a-site").value + " " + S.$("oxide-b-site").value;
    },
  ],
  [
    "calculator (ceramics)",
    async () => {
      const S = window.__smoke;
      await S.view("calc");
      document.querySelector('.mode-btn[data-mode="ceramic"]').click();
      const example = S.$("ceramic-example");
      example.value = Array.from(example.options).find((o) => o.value).value;
      example.dispatchEvent(new Event("change", { bubbles: true }));
      S.$("ceramic-calculate").click();
      await S.waitFor("the ceramic descriptors", () => S.$("ceramic-results").textContent.trim().length > 40, 30000, S.$("ceramic-panel"));
      S.clean(S.$("ceramic-panel"), "the ceramic calculator");
      document.querySelector('.mode-btn[data-mode="alloy"]').click();
      return "example " + S.$("ceramic-metals").value;
    },
  ],
  [
    "predictions panel (engine start, dataset build, hardness, phase sets, domain)",
    async (version) => {
      const S = window.__smoke;
      await S.view("calc");
      const start = await S.waitFor("the Start button", () => S.$("predict-gate").querySelector('[data-gate="start"]'), 10000);
      start.click();
      const panel = S.$("predict-panel");
      await S.waitFor(
        "hardness, the phase prediction set and the domain check",
        () =>
          S.$("predict-gate").classList.contains("is-ready") &&
          /HV/.test(S.$("predict-engine").textContent) &&
          /single-phase|multi-phase/.test(S.$("predict-engine").textContent) &&
          /Resembles the dataset\?\s*(yes|no)/.test(S.$("predict-engine").textContent),
        600000,
        panel
      );
      S.clean(panel, "the predictions panel");
      if (!S.$("predict-gate").textContent.includes("hea-bench " + version)) throw new Error("engine reports: " + S.$("predict-gate").textContent.trim());
      return S.$("predict-gate").textContent.trim();
    },
  ],
  [
    "dataset tab (table, CSV, measured records)",
    async () => {
      const S = window.__smoke;
      const view = await S.view("dataset");
      await S.waitFor("dataset rows", () => S.rows("dataset-tbody") > 5, 300000, view);
      await S.waitFor("measured records", () => S.rows("measured-tbody") > 5, 120000, view);
      const csv = await S.download(() => S.$("dataset-download").click(), "the dataset CSV");
      if (!/composition/.test(csv.split("\n")[0])) throw new Error("unexpected dataset CSV header: " + csv.split("\n")[0]);
      S.clean(view, "the dataset tab");
      return S.rows("dataset-tbody") + " rows shown, " + S.rows("measured-tbody") + " measured records, CSV " + csv.length + " bytes";
    },
  ],
  [
    "benchmark tab (frozen digests, baseline rerun, example upload with the gap, coverage)",
    async () => {
      const S = window.__smoke;
      const view = await S.view("benchmark");
      await S.waitFor("the frozen split digests", () => (view.textContent.match(/matches the frozen split/g) || []).length >= 2, 300000, view);
      if (/differs from the frozen split/.test(view.textContent)) throw new Error("a split differs from its frozen digest");
      const run = await S.waitFor("a rule baseline", () => S.$("benchmark-baselines-body").querySelector('[data-run^="rule:"]'), 60000, view);
      const model = run.getAttribute("data-run");
      run.click();
      await S.waitFor(model + " rerun", () => /reproduced here/.test(S.$("benchmark-baselines-body").querySelector('[data-run="' + model + '"]').closest("tr").textContent), 300000, view);
      const example = await S.download(() => S.$("benchmark-example").click(), "the example predictions file");
      const input = S.$("benchmark-upload-file");
      const files = new DataTransfer();
      files.items.add(new File([example], "example-predictions.csv", { type: "text/csv" }));
      input.files = files.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      await S.waitFor("the score with its gap", () => /Gap/.test(S.$("benchmark-score-body").textContent) && S.$("benchmark-score-body").querySelectorAll("tbody tr").length === 4, 300000, view);
      S.$("benchmark-coverage-run").click();
      await S.waitFor("the coverage study", () => S.$("benchmark-coverage-body").querySelectorAll("tbody tr").length > 0, 600000, view);
      S.clean(view, "the benchmark tab");
      return model + " reproduced, example file scored, " + S.$("benchmark-coverage-body").querySelectorAll("tbody tr").length + " coverage rows";
    },
  ],
  [
    "design tab (search, experiment planning, campaign file)",
    async () => {
      const S = window.__smoke;
      const view = await S.view("design");
      S.$("search-form").requestSubmit();
      await S.waitFor("search results", () => S.$("search-results").querySelectorAll("tbody tr").length > 0, 300000, view);
      const row = S.$("campaign-obs-tbody").querySelector("tr");
      row.querySelector('[data-k="composition"]').value = "AlCoCrFe";
      row.querySelector('[data-k="value"]').value = "480";
      S.$("campaign-suggest").click();
      await S.waitFor("the campaign suggestions", () => S.$("campaign-results").querySelectorAll("tbody tr").length > 0, 300000, view);
      const saved = JSON.parse(await S.download(() => S.$("campaign-save").click(), "the campaign file"));
      if (!saved.observations || saved.observations.length !== 1) throw new Error("the saved campaign lost its observation");
      S.clean(view, "the design tab");
      return S.$("search-results").querySelectorAll("tbody tr").length + " search results, " + S.$("campaign-results").querySelectorAll("tbody tr").length + " suggestions";
    },
  ],
  [
    "equations (MathJax)",
    async () => {
      const S = window.__smoke;
      await S.view("theory");
      await S.waitFor("typeset equations", () => document.querySelector('.view[data-view-panel="theory"] mjx-container'), 60000);
      // What the MathJax menu loads on demand: the other renderer and the
      // accessibility tools. A pruned web/mathjax/ must keep all of them.
      const parts = ["output/svg", "a11y/assistive-mml", "a11y/explorer", "a11y/complexity", "a11y/semantic-enrich", "ui/safe"];
      for (const part of parts) await MathJax.loader.load(part);
      return document.querySelectorAll("mjx-container").length + " equations typeset, menu components load";
    },
  ],
];

(async () => {
  const meta = await (await fetch("http://127.0.0.1:" + port + "/json/version")).json();
  const cdp = await connect(meta.webSocketDebuggerUrl);
  const problems = [];
  const body = fs.readFileSync(peivastePath).toString("base64");
  let served = 0;

  // Every page and worker session: report errors, answer the Peivaste
  // download locally, and attach to the workers it starts.
  function instrument(sessionId) {
    return Promise.all([
      cdp.send("Runtime.enable", {}, sessionId),
      cdp.send("Log.enable", {}, sessionId).catch(() => {}),
      cdp.send("Fetch.enable", { patterns: [{ urlPattern: "*" + peivasteUrl.split("/").pop() }] }, sessionId).catch(() => {}),
      cdp.send("Target.setAutoAttach", { autoAttach: true, waitForDebuggerOnStart: true, flatten: true }, sessionId).catch(() => {}),
    ]);
  }

  cdp.on((msg) => {
    const p = msg.params || {};
    if (msg.method === "Target.attachedToTarget") {
      instrument(p.sessionId).finally(() => cdp.send("Runtime.runIfWaitingForDebugger", {}, p.sessionId).catch(() => {}));
    } else if (msg.method === "Fetch.requestPaused") {
      if (p.request.url === peivasteUrl) {
        served += 1;
        cdp
          .send(
            "Fetch.fulfillRequest",
            {
              requestId: p.requestId,
              responseCode: 200,
              responseHeaders: [
                { name: "Content-Type", value: "text/csv" },
                { name: "Access-Control-Allow-Origin", value: "*" },
              ],
              body,
            },
            msg.sessionId
          )
          .catch((e) => problems.push("could not answer the Peivaste download: " + e.message));
      } else {
        cdp.send("Fetch.continueRequest", { requestId: p.requestId }, msg.sessionId).catch(() => {});
      }
    } else if (msg.method === "Runtime.exceptionThrown") {
      const d = p.exceptionDetails || {};
      problems.push("uncaught: " + ((d.exception && d.exception.description) || d.text));
    } else if (msg.method === "Runtime.consoleAPICalled" && (p.type === "error" || p.type === "assert")) {
      problems.push("console error: " + p.args.map((a) => (a.value !== undefined ? a.value : a.description)).join(" "));
    } else if (msg.method === "Log.entryAdded" && p.entry.level === "error") {
      problems.push("log error: " + p.entry.text + (p.entry.url ? " (" + p.entry.url + ")" : ""));
    }
  });

  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  await instrument(sessionId);
  await cdp.send("Page.enable", {}, sessionId);
  const loaded = new Promise((resolve) => cdp.on((msg) => msg.sessionId === sessionId && msg.method === "Page.loadEventFired" && resolve()));
  await cdp.send("Page.navigate", { url: appUrl }, sessionId);
  await loaded;

  async function evaluate(source) {
    const r = await cdp.send("Runtime.evaluate", { expression: source, awaitPromise: true, returnByValue: true }, sessionId);
    if (r.exceptionDetails) {
      const d = r.exceptionDetails;
      throw new Error(((d.exception && d.exception.description) || d.text).split("\n")[0]);
    }
    return r.result.value;
  }

  await evaluate("(" + HELPERS.toString() + ")()");
  const steps = [];
  for (const [name, step] of STEPS) {
    const started = Date.now();
    let ok = true;
    let detail;
    try {
      detail = await evaluate("(" + step.toString() + ")(" + JSON.stringify(version) + ")");
    } catch (e) {
      ok = false;
      detail = e.message;
    }
    steps.push({ name, ok, detail, seconds: Math.round((Date.now() - started) / 100) / 10 });
  }
  cdp.close();
  report({ steps, problems, peivaste_served: served });
})().catch((e) => report({ fatal: String((e && e.stack) || e) }));
