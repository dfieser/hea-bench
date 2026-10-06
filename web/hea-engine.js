/* HEA-Bench engine client: a lazy handle on hea-engine-worker.js.
 *
 * Nothing loads until a feature asks for the engine (the desktop app asks
 * at launch); the first request starts the worker and every later one
 * reuses it. The engine is about 28 MB: the website fetches it once and
 * the browser keeps it, the desktop exe carries it. API on window.HEAEngine:
 *
 *   start()                          -> Promise(info)   boot, idempotent
 *   call(method, params, onProgress) -> Promise(result) one bridge call
 *   ensureCorpus(version, onProgress)-> Promise         build once per release
 *   fetchPeivaste(onProgress)        -> Promise         get and keep the Peivaste file
 *   onStatus(listener)               state changes: {state, message, fraction, info, error}
 *   restart()                        stop a long run and boot afresh
 *   available()                      false on file:// (browsers block workers there)
 */
(function () {
  "use strict";

  // The page loads this file as hea-engine.js?v=<version>; the worker gets
  // the same stamp so a release never runs an old worker with a new page.
  var STAMP = (function () {
    var src = document.currentScript && document.currentScript.src;
    return src && src.indexOf("?") >= 0 ? src.slice(src.indexOf("?")) : "";
  })();
  var worker = null;
  var ready = null;
  var nextId = 1;
  var pending = {};
  var listeners = [];
  var status = { state: "idle", message: "", fraction: 0, info: null, error: null, slow: false };
  // A boot step that sends no progress for this long is flagged as slow, so
  // the page can offer a restart instead of a progress bar that never moves.
  // The boot itself keeps running: a slow device may still finish.
  var SLOW_AFTER_MS = 60000;
  var watchdog = null;

  function armWatchdog() {
    clearTimeout(watchdog);
    watchdog = setTimeout(function () {
      if (status.state === "loading") emit({ slow: true });
    }, SLOW_AFTER_MS);
  }

  function emit(patch) {
    for (var key in patch) status[key] = patch[key];
    listeners.forEach(function (listener) {
      try {
        listener(status);
      } catch (error) {
        /* a broken listener must not stop the others */
      }
    });
  }

  function available() {
    return typeof Worker !== "undefined" && location.protocol !== "file:";
  }

  function failAll(message) {
    Object.keys(pending).forEach(function (id) {
      pending[id].reject(new Error(message));
      delete pending[id];
    });
  }

  function start() {
    if (ready) return ready;
    if (!available()) {
      var message =
        "The prediction engine needs the app to be served over http(s): browsers block it on " +
        "file:// pages. Use the website or the desktop app, or run " +
        "\"python -m http.server -d web\" in the repository.";
      emit({ state: "unavailable", error: message });
      ready = Promise.reject(new Error(message));
      ready.catch(function () {});
      return ready;
    }
    emit({ state: "loading", message: "Starting the engine", fraction: 0.01, error: null, slow: false });
    armWatchdog();
    worker = new Worker("hea-engine-worker.js" + STAMP);
    ready = new Promise(function (resolve, reject) {
      worker.onmessage = function (event) {
        var data = event.data;
        if (data.boot) {
          if (data.boot.done) {
            clearTimeout(watchdog);
            emit({ state: "ready", message: "Ready", fraction: 1, info: data.boot.info, slow: false });
            resolve(data.boot.info);
          } else {
            armWatchdog();
            emit({ message: data.boot.message, fraction: data.boot.fraction, slow: false });
          }
          return;
        }
        if (data.bootError) {
          clearTimeout(watchdog);
          emit({ state: "error", error: data.bootError });
          failAll(data.bootError);
          reject(new Error(data.bootError));
          return;
        }
        var entry = pending[data.id];
        if (!entry) return;
        if (data.progress) {
          if (entry.onProgress) entry.onProgress(data.progress);
          return;
        }
        delete pending[data.id];
        if (data.ok) entry.resolve(data.result);
        else entry.reject(new Error(data.error));
      };
      worker.onerror = function (event) {
        clearTimeout(watchdog);
        var message = "The engine failed to start: " + (event.message || "unknown error") + ".";
        emit({ state: "error", error: message });
        failAll(message);
        reject(new Error(message));
      };
    });
    ready.catch(function () {});
    return ready;
  }

  function call(method, params, onProgress) {
    return start().then(function () {
      return new Promise(function (resolve, reject) {
        var id = nextId++;
        pending[id] = { resolve: resolve, reject: reject, onProgress: onProgress };
        worker.postMessage({ id: id, method: method, params: params || {} });
      });
    });
  }

  function ensureCorpus(version, onProgress) {
    return call("ensure_corpus", { version: version || "0.1.0" }, onProgress);
  }

  function fetchPeivaste(onProgress) {
    return call("fetch_peivaste", {}, onProgress);
  }

  function restart() {
    clearTimeout(watchdog);
    if (worker) worker.terminate();
    worker = null;
    ready = null;
    failAll("Stopped.");
    emit({ state: "idle", message: "", fraction: 0, info: null, error: null, slow: false });
    return start();
  }

  function onStatus(listener) {
    listeners.push(listener);
    listener(status);
  }

  window.HEAEngine = {
    available: available,
    start: start,
    call: call,
    ensureCorpus: ensureCorpus,
    fetchPeivaste: fetchPeivaste,
    restart: restart,
    onStatus: onStatus,
    status: function () {
      return status;
    },
  };
})();
