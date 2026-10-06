/* HEA-Bench engine worker: the real hea_bench Python package, in the browser.
 *
 * Boot: load the vendored Pyodide runtime (engine/pyodide/, assembled at
 * deploy time by tools/build_web_engine.py), numpy and scikit-learn, unpack
 * engine/hea-bench.zip to /repo, mount IndexedDB at /persist so the built
 * corpus and the Peivaste download survive reloads, then import
 * hea_bench.webapp. Every request {id, method, params} runs
 * webapp.call(method, json) and answers {id, ok, result | error}; long calls
 * post {id, progress} on the way. Requests run one at a time, in order.
 *
 * Between requests the worker prepares what the tabs need, one short step
 * at a time (webapp.warm_next / webapp.warm): it builds the corpus from
 * the persisted download, loads it, and fits the models, which it keeps
 * in IndexedDB (HEA_BENCH_MODEL_CACHE) so a returning visitor loads them
 * instead of refitting. A request from the page always goes before the
 * next step, so a click never waits behind more than one.
 */
"use strict";

var pyodide = null;
var webapp = null;
var currentId = null;
var requests = [];
var pumping = false;
// Give the page's first requests (a gate's corpus build, a prediction) a
// moment to arrive before the background preparation starts.
var WARM_DELAY_MS = 400;
var PEIVASTE_CACHE = "/persist/peivaste.csv";

function post(message) {
  self.postMessage(message);
}

function bootProgress(message, fraction) {
  post({ boot: { message: message, fraction: fraction } });
}

function syncfs(populate) {
  return new Promise(function (resolve, reject) {
    pyodide.FS.syncfs(populate, function (error) {
      if (error) reject(error);
      else resolve();
    });
  });
}

function exists(path) {
  try {
    pyodide.FS.stat(path);
    return true;
  } catch (error) {
    return false;
  }
}

function callPython(method, params) {
  var envelope = JSON.parse(webapp.call(method, JSON.stringify(params || {})));
  if (!envelope.ok) {
    var error = new Error(envelope.error);
    error.pythonType = envelope.type;
    throw error;
  }
  return envelope.result;
}

async function fetchBytes(url) {
  var response = await fetch(url);
  if (!response.ok) throw new Error("could not download " + url + " (HTTP " + response.status + ")");
  return new Uint8Array(await response.arrayBuffer());
}

async function boot() {
  bootProgress("Loading the Python runtime", 0.05);
  importScripts("engine/pyodide/pyodide.js");
  var manifest = await (await fetch("engine/manifest.json", { cache: "no-cache" })).json();
  pyodide = await self.loadPyodide({ indexURL: new URL("engine/pyodide/", self.location.href).href });
  bootProgress("Loading numpy, scipy and scikit-learn", 0.3);
  await pyodide.loadPackage(["numpy", "scikit-learn"], { messageCallback: function () {} });
  bootProgress("Loading hea-bench " + manifest.hea_bench_version, 0.8);
  var archive = await fetchBytes("engine/hea-bench.zip?sha=" + manifest.zip_sha256);
  pyodide.unpackArchive(archive, "zip", { extractDir: "/repo" });
  pyodide.FS.mkdirTree("/persist");
  pyodide.FS.mount(pyodide.FS.filesystems.IDBFS, {}, "/persist");
  await syncfs(true);
  // The corpus and the fitted models are keyed by package version: a new
  // release rebuilds them from the persisted raw download, so stale ones
  // can never be read.
  var corpusDir = "/persist/corpus-" + manifest.hea_bench_version;
  var modelDir = "/persist/models-" + manifest.hea_bench_version;
  pyodide.FS.readdir("/persist").forEach(function (name) {
    var path = "/persist/" + name;
    if ((name.indexOf("corpus-") === 0 && path !== corpusDir) || (name.indexOf("models-") === 0 && path !== modelDir)) {
      removeTree(path);
    }
  });
  pyodide.runPython(
    "import os, sys\n" +
      "sys.path.insert(0, '/repo/src')\n" +
      "os.environ['HEA_BENCH_BENCHMARK_DIR'] = " + JSON.stringify(corpusDir) + "\n" +
      "os.environ['HEA_BENCH_MODEL_CACHE'] = " + JSON.stringify(modelDir) + "\n" +
      "import hea_bench.webapp\n"
  );
  webapp = pyodide.pyimport("hea_bench.webapp");
  webapp.set_progress(function (message, fraction) {
    if (currentId !== null) post({ id: currentId, progress: { message: message, fraction: fraction } });
  });
  // A download persisted on an earlier visit lets the background steps
  // rebuild the corpus without asking again.
  if (exists(PEIVASTE_CACHE) && !callPython("peivaste_source").installed) {
    try {
      callPython("peivaste_install", { path: PEIVASTE_CACHE });
    } catch (error) {
      pyodide.FS.unlink(PEIVASTE_CACHE);
    }
  }
  var info = callPython("engine_info");
  info.pyodide_version = manifest.pyodide_version;
  bootProgress("Ready", 1);
  return info;
}

function removeTree(path) {
  var FS = pyodide.FS;
  FS.readdir(path).forEach(function (name) {
    if (name === "." || name === "..") return;
    var child = path + "/" + name;
    if (FS.isDir(FS.stat(child).mode)) removeTree(child);
    else FS.unlink(child);
  });
  FS.rmdir(path);
}

// Worker-side steps that need the network or IndexedDB, then the library.
//
// The Peivaste file is the one input neither the website nor the desktop
// exe may ship (its authors have not licensed redistribution yet), so it
// comes from their repository once, is checked against the pinned hash,
// and is kept in IndexedDB. Everything after that works offline.
async function fetchPeivaste() {
  if (callPython("peivaste_source").installed) return { installed: true };
  if (!exists(PEIVASTE_CACHE)) {
    var source = callPython("peivaste_source");
    post({ id: currentId, progress: { message: "Downloading the Peivaste dataset from its authors' repository (6.4 MB, once)", fraction: 0.05 } });
    var bytes;
    try {
      bytes = await fetchBytes(source.url);
    } catch (error) {
      throw new Error(
        "The dataset needs the Peivaste file from its authors' repository once (6.4 MB), and the " +
        "download failed, most likely because this device is offline. Connect to the internet once " +
        "and try again: the app keeps the file, so it works offline after that. (" + error.message + ")"
      );
    }
    pyodide.FS.writeFile("/tmp/peivaste.csv", bytes);
    callPython("peivaste_install", { path: "/tmp/peivaste.csv" });
    pyodide.FS.writeFile(PEIVASTE_CACHE, bytes);
    await syncfs(false);
  } else {
    callPython("peivaste_install", { path: PEIVASTE_CACHE });
  }
  return { installed: true };
}

async function ensureCorpus(version) {
  if (callPython("dataset_status").built[version]) return { built: true, version: version };
  await fetchPeivaste();
  post({ id: currentId, progress: { message: "Building corpus v" + version + " (about a minute, once per release)", fraction: 0.3 } });
  callPython("dataset_build", { version: version });
  await syncfs(false);
  return { built: true, version: version };
}

async function handle(message) {
  currentId = message.id;
  try {
    var result =
      message.method === "ensure_corpus"
        ? await ensureCorpus((message.params && message.params.version) || "0.1.0")
        : message.method === "fetch_peivaste"
        ? await fetchPeivaste()
        : callPython(message.method, message.params);
    post({ id: message.id, ok: true, result: result });
  } catch (error) {
    post({ id: message.id, ok: false, error: String(error && error.message ? error.message : error) });
  } finally {
    currentId = null;
  }
}

function pause(ms) {
  return new Promise(function (resolve) {
    setTimeout(resolve, ms);
  });
}

async function persist() {
  try {
    await syncfs(false);
  } catch (error) {
    /* storage full or blocked: the next visit fits the models again */
  }
}

// One loop serves the page's requests in order and, whenever none is
// waiting, runs the next background step. Python calls are synchronous,
// so the pause after each item is what lets new requests arrive.
async function pump() {
  if (pumping) return;
  pumping = true;
  try {
    await booted;
  } catch (error) {
    var reason = "the engine did not start: " + String(error && error.message ? error.message : error);
    requests.splice(0).forEach(function (message) {
      post({ id: message.id, ok: false, error: reason });
    });
    pumping = false;
    return;
  }
  for (;;) {
    if (requests.length) {
      await handle(requests.shift());
    } else {
      var step = null;
      try {
        step = callPython("warm_next");
      } catch (error) {
        step = null;
      }
      if (!step) break;
      try {
        callPython("warm", { step: step });
      } catch (error) {
        /* reported when the page asks for that feature */
      }
    }
    await persist();
    await pause(0);
  }
  pumping = false;
}

var booted = boot().then(
  function (info) {
    post({ boot: { message: "Ready", fraction: 1, done: true, info: info } });
    pause(WARM_DELAY_MS).then(pump);
  },
  function (error) {
    post({ bootError: String(error && error.message ? error.message : error) });
    throw error;
  }
);
booted.catch(function () {});

self.onmessage = function (event) {
  requests.push(event.data);
  pump();
};
