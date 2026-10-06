/* HEA-Bench engine worker: the real hea_bench Python package, in the browser.
 *
 * Boot: load the vendored Pyodide runtime (engine/pyodide/, assembled at
 * deploy time by tools/build_web_engine.py), numpy and scikit-learn, unpack
 * engine/hea-bench.zip to /repo, mount IndexedDB at /persist so the built
 * corpus and the Peivaste download survive reloads, then import
 * hea_bench.webapp. Every request {id, method, params} runs
 * webapp.call(method, json) and answers {id, ok, result | error}; long calls
 * post {id, progress} on the way. Requests run one at a time, in order.
 */
"use strict";

var pyodide = null;
var webapp = null;
var currentId = null;
var queue = Promise.resolve();

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
  // The corpus is keyed by package version: a new release rebuilds it from
  // the persisted raw download, so a stale corpus can never be read.
  var corpusDir = "/persist/corpus-" + manifest.hea_bench_version;
  pyodide.FS.readdir("/persist").forEach(function (name) {
    if (name.indexOf("corpus-") === 0 && "/persist/" + name !== corpusDir) removeTree("/persist/" + name);
  });
  pyodide.runPython(
    "import os, sys\n" +
      "sys.path.insert(0, '/repo/src')\n" +
      "os.environ['HEA_BENCH_BENCHMARK_DIR'] = " + JSON.stringify(corpusDir) + "\n" +
      "import hea_bench.webapp\n"
  );
  webapp = pyodide.pyimport("hea_bench.webapp");
  webapp.set_progress(function (message, fraction) {
    if (currentId !== null) post({ id: currentId, progress: { message: message, fraction: fraction } });
  });
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
async function ensureCorpus(version) {
  if (callPython("dataset_status").built[version]) return { built: true, version: version };
  var source = callPython("peivaste_source");
  if (!source.installed) {
    var cached = "/persist/peivaste.csv";
    if (!exists(cached)) {
      post({ id: currentId, progress: { message: "Downloading the Peivaste dataset from its authors' repository (6.4 MB)", fraction: 0.05 } });
      var bytes = await fetchBytes(source.url);
      pyodide.FS.writeFile("/tmp/peivaste.csv", bytes);
      callPython("peivaste_install", { path: "/tmp/peivaste.csv" });
      pyodide.FS.writeFile(cached, bytes);
      await syncfs(false);
    } else {
      callPython("peivaste_install", { path: cached });
    }
  }
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
        : callPython(message.method, message.params);
    post({ id: message.id, ok: true, result: result });
  } catch (error) {
    post({ id: message.id, ok: false, error: String(error && error.message ? error.message : error) });
  } finally {
    currentId = null;
  }
}

var booted = boot().then(
  function (info) {
    post({ boot: { message: "Ready", fraction: 1, done: true, info: info } });
  },
  function (error) {
    post({ bootError: String(error && error.message ? error.message : error) });
    throw error;
  }
);

self.onmessage = function (event) {
  var message = event.data;
  queue = queue
    .catch(function () {})
    .then(function () {
      return booted.then(
        function () {
          return handle(message);
        },
        function (error) {
          post({ id: message.id, ok: false, error: "the engine did not start: " + String(error && error.message ? error.message : error) });
        }
      );
    });
};
