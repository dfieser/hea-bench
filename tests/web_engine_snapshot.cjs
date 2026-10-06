// Drive the vendored browser engine (web/engine/, built by
// tools/build_web_engine.py) under Node: the same Pyodide runtime, wheels
// and package zip the app loads, called through hea_bench.webapp exactly as
// hea-engine-worker.js calls it. tests/test_web_engine.py compares every
// result with CPython.
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const engineDir = path.join(root, "web", "engine");
const { loadPyodide } = require(path.join(engineDir, "pyodide", "pyodide.js"));
const calls = JSON.parse(fs.readFileSync(path.join(__dirname, "data", "web_engine_calls.json"), "utf8"));

(async () => {
  const py = await loadPyodide({ indexURL: path.join(engineDir, "pyodide") + path.sep });
  await py.loadPackage(["numpy", "scikit-learn"], { messageCallback: () => {} });
  py.unpackArchive(new Uint8Array(fs.readFileSync(path.join(engineDir, "hea-bench.zip"))), "zip", { extractDir: "/repo" });
  const peivaste = path.join(root, "data", "raw", "peivaste", "dataset11252_79.csv");
  const havePeivaste = fs.existsSync(peivaste);
  if (havePeivaste) {
    py.FS.writeFile("/tmp/peivaste.csv", new Uint8Array(fs.readFileSync(peivaste)));
  }
  py.runPython("import sys\nsys.path.insert(0, '/repo/src')\nimport hea_bench.webapp\n");
  const webapp = py.pyimport("hea_bench.webapp");
  const call = (method, params) => JSON.parse(webapp.call(method, JSON.stringify(params || {})));
  const out = { have_peivaste: havePeivaste, results: {} };
  if (havePeivaste) {
    const installed = call("peivaste_install", { path: "/tmp/peivaste.csv" });
    if (!installed.ok) throw new Error(installed.error);
    // Both versions, as the app builds them: the dataset view opens
    // v0.2.0, while the benchmark and the predictions use v0.1.0.
    for (const version of ["0.1.0", "0.2.0"]) {
      const built = call("dataset_build", { version });
      if (!built.ok) throw new Error(built.error);
    }
  }
  for (const entry of calls) {
    if (entry.needs_corpus && !havePeivaste) continue;
    out.results[entry.name] = call(entry.method, entry.params);
  }
  process.stdout.write(JSON.stringify(out));
})().catch((error) => {
  process.stderr.write(String(error && error.stack ? error.stack : error));
  process.exit(1);
});
