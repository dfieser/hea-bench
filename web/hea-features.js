/* HEA-Bench app features beyond the descriptor calculator.
 *
 * Instant, in-page arithmetic (tier A properties, ceramics) comes from the
 * parity-tested JavaScript core. Everything fitted or data-backed (hardness,
 * phase prediction sets, the domain check, the dataset, the benchmark, the
 * composition search, experiment planning) is computed by the hea-bench
 * Python library itself, running in the engine worker (hea-engine.js), so
 * the app shows the library's own numbers. Loaded after the calculator's
 * scripts; it only reads the page and listens for "hea:alloy-result".
 */
(function () {
  "use strict";

  var core = window.HeaCalculatorCore;
  var engine = window.HEAEngine;
  if (!core || !engine) return;

  var AUTOSTART_KEY = "hea-bench-engine-autostart";
  var corpusReady = {}; // corpus version -> built in this engine session

  function isBuilt(version) {
    var info = engine.status().info;
    return !!(corpusReady[version] || (info && info.built && info.built[version]));
  }
  var HARDNESS_MIN_ROWS = 50; // hea_bench.properties.hardness.N_MIN

  // ---------------------------------------------------------------- helpers

  function $(id) {
    return document.getElementById(id);
  }

  function esc(value) {
    return String(value === null || value === undefined ? "" : value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function num(x, digits) {
    if (x === null || x === undefined || typeof x !== "number" || !isFinite(x)) return "n/a";
    return x.toFixed(digits === undefined ? 3 : digits);
  }

  function pct(x, digits) {
    if (x === null || x === undefined || !isFinite(x)) return "n/a";
    return (100 * x).toFixed(digits === undefined ? 1 : digits) + "%";
  }

  function signed(x, digits) {
    if (x === null || x === undefined || !isFinite(x)) return "n/a";
    var d = digits === undefined ? 3 : digits;
    var r = Number(x.toFixed(d));
    return r === 0 ? (0).toFixed(d) : (r > 0 ? "+" : "-") + Math.abs(r).toFixed(d);
  }

  function int(x) {
    return typeof x === "number" ? x.toLocaleString("en-US") : "n/a";
  }

  // Composition dict -> HTML with at.% subscripts, in the given key order.
  function compHtml(comp) {
    return Object.keys(comp)
      .map(function (el) {
        var p = 100 * comp[el];
        return esc(el) + "<sub>" + (Math.abs(p - Math.round(p)) < 0.05 ? Math.round(p) : p.toFixed(1)) + "</sub>";
      })
      .join("");
  }

  // Composition dict -> a formula the calculator's parser reads (percent amounts).
  function compText(comp) {
    return Object.keys(comp)
      .map(function (el) {
        return el + parseFloat((100 * comp[el]).toFixed(2));
      })
      .join("");
  }

  function parseFormula(text) {
    var source = String(text || "").replace(/\s+/g, "");
    if (!source) throw new Error("Enter a composition, for example HfNbTaTiZr.");
    var re = /([A-Z][a-z]?)(\d*\.?\d*)/g;
    var out = {};
    var consumed = "";
    var match;
    while ((match = re.exec(source)) !== null) {
      if (!match[0]) break;
      consumed += match[0];
      var amount = match[2] === "" ? 1 : parseFloat(match[2]);
      if (!isFinite(amount) || amount <= 0) throw new Error("Amounts must be positive numbers (" + match[0] + ").");
      out[match[1]] = (out[match[1]] || 0) + amount;
    }
    if (consumed !== source) throw new Error("Could not read \"" + text + "\". Use element symbols with optional amounts, for example Ti0.5Zr0.5.");
    return out;
  }

  function elementsList(text) {
    return String(text || "")
      .split(/[\s,;]+/)
      .map(function (s) {
        return s.trim();
      })
      .filter(Boolean)
      .map(function (s) {
        return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
      });
  }

  function download(filename, text, type) {
    var blob = new Blob([text], { type: type || "text/plain" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      URL.revokeObjectURL(url);
      a.remove();
    }, 0);
  }

  function readFile(input) {
    return new Promise(function (resolve, reject) {
      var file = input.files && input.files[0];
      input.value = "";
      if (!file) return reject(new Error("No file chosen."));
      var reader = new FileReader();
      reader.onload = function () {
        resolve(String(reader.result));
      };
      reader.onerror = function () {
        reject(new Error("Could not read " + file.name + "."));
      };
      reader.readAsText(file);
    });
  }

  function showView(name) {
    var tab = document.querySelector('.titlebar__tabs .tab[data-view="' + name + '"]');
    if (tab) tab.click();
  }

  function openInCalculator(comp) {
    var alloyMode = document.querySelector('.mode-btn[data-mode="alloy"]');
    if (alloyMode) alloyMode.click();
    showView("calc");
    $("formula-input").value = compText(comp);
    $("parse-formula").click();
    $("calculate").click();
  }

  function errorHtml(error) {
    return '<p class="feature-error">' + esc(error && error.message ? error.message : error) + "</p>";
  }

  function onShow(viewName, callback) {
    var view = document.querySelector('.views .view[data-view-panel="' + viewName + '"]');
    if (!view) return;
    var fire = function () {
      if (view.classList.contains("view--active")) callback();
    };
    new MutationObserver(fire).observe(view, { attributes: true, attributeFilter: ["class"] });
    fire();
  }

  function autostart() {
    try {
      return localStorage.getItem(AUTOSTART_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  engine.onStatus(function (status) {
    if (status.state === "ready") {
      try {
        localStorage.setItem(AUTOSTART_KEY, "1");
      } catch (e) {
        /* storage unavailable */
      }
    }
  });

  // ------------------------------------------------------------ engine gate
  //
  // One status box per feature. It explains what will load, starts the
  // engine (and builds the dataset when the feature needs it), shows
  // progress, and reports failures with the library's own message.

  function Gate(container, options) {
    this.el = container;
    this.needsCorpus = !!options.needsCorpus;
    this.version = options.version || function () {
      return "0.1.0";
    };
    this.what = options.what;
    this.onReady = options.onReady;
    this.task = null; // {message, fraction} while a feature step runs
    this.error = null;
    var self = this;
    engine.onStatus(function () {
      self.render();
    });
  }

  Gate.prototype.render = function () {
    var status = engine.status();
    var el = this.el;
    el.classList.remove("is-ready", "is-error");
    var text;
    var button = "";
    var fraction = null;
    if (!engine.available()) {
      el.classList.add("is-error");
      text = esc(status.error || "The engine needs the app to be served over http(s).");
    } else if (this.error) {
      el.classList.add("is-error");
      text = esc(this.error);
      button = '<button type="button" class="secondary" data-gate="retry">Try again</button>';
    } else if (status.state === "error") {
      el.classList.add("is-error");
      text = esc(status.error);
      button = '<button type="button" class="secondary" data-gate="retry">Try again</button>';
    } else if (status.state === "idle") {
      text =
        "<b>" + esc(this.what) + "</b> This runs the hea-bench Python library inside the page. " +
        "The first start downloads about 30 MB, which the browser then keeps" +
        (this.needsCorpus
          ? ", and builds the alloy dataset once per release (it fetches the Peivaste file from its authors' repository and checks its hash)."
          : ".");
      button = '<button type="button" class="primary" data-gate="start">Start</button>';
    } else if (status.state === "loading") {
      text = esc(status.message || "Starting the engine") + "…";
      fraction = status.fraction;
      if (status.slow) {
        text += " This is taking longer than usual. If nothing changes, restart the engine.";
        button = '<button type="button" class="secondary" data-gate="retry">Restart</button>';
      }
    } else if (this.task) {
      text = esc(this.task.message) + "…";
      fraction = this.task.fraction;
      button = '<button type="button" class="ghost" data-gate="stop">Stop</button>';
    } else if (this.needsCorpus && !isBuilt(this.version())) {
      text = "Engine ready. The dataset is not built yet.";
      button = '<button type="button" class="primary" data-gate="start">Build the dataset</button>';
    } else {
      el.classList.add("is-ready");
      var info = status.info || {};
      text =
        "Computed by hea-bench " + esc(info.hea_bench_version) + " in this page (Python " +
        esc(info.python) + ", scikit-learn " + esc(info.scikit_learn) + ", Pyodide " + esc(info.pyodide_version) + ").";
    }
    el.innerHTML =
      '<div class="engine-gate__row"><div class="engine-gate__text">' + text + "</div>" + button + "</div>" +
      (fraction === null || fraction === undefined
        ? ""
        : '<div class="engine-gate__bar"><span style="width:' + Math.round(100 * Math.max(0.02, fraction)) + '%"></span></div>');
  };

  Gate.prototype.bind = function () {
    var self = this;
    this.el.addEventListener("click", function (event) {
      var action = event.target && event.target.getAttribute && event.target.getAttribute("data-gate");
      if (action === "start") self.ensure().then(self.onReady, function () {});
      if (action === "retry") {
        self.error = null;
        engine.restart();
        self.ensure().then(self.onReady, function () {});
      }
      if (action === "stop") {
        self.task = null;
        engine.restart();
      }
    });
    this.render();
    return this;
  };

  // Engine up (and the dataset built, if needed). Resolves when usable.
  Gate.prototype.ensure = function () {
    var self = this;
    var version = this.version();
    self.error = null;
    return engine
      .start()
      .then(function () {
        if (!self.needsCorpus || isBuilt(version)) return null;
        return self.run("Preparing the dataset", function (progress) {
          return engine.ensureCorpus(version, progress);
        }).then(function () {
          corpusReady[version] = true;
        });
      })
      .then(
        function () {
          self.render();
        },
        function (error) {
          self.error = error.message;
          self.render();
          throw error;
        }
      );
  };

  // Run one engine step with progress shown in this gate.
  Gate.prototype.run = function (message, step) {
    var self = this;
    self.task = { message: message, fraction: 0.02 };
    self.render();
    return step(function (progress) {
      self.task = { message: progress.message, fraction: progress.fraction };
      self.render();
    }).then(
      function (result) {
        self.task = null;
        self.render();
        return result;
      },
      function (error) {
        self.task = null;
        self.render();
        throw error;
      }
    );
  };

  // ------------------------------------------- calculator: predictions panel

  var predict = {
    comp: null,
    running: false,
    rerun: false,
    started: false,
    processing: [],
  };
  var predictGate = new Gate($("predict-gate"), {
    what: "Hardness, phase prediction sets and the dataset check.",
    needsCorpus: true,
    onReady: function () {
      predict.started = true;
      runPredictions();
    },
  }).bind();

  function tierACards(comp) {
    var cards = [];
    var density = null;
    var breakdown = null;
    try {
      density = core.tierADensity(comp);
      breakdown = core.costBreakdown(comp);
    } catch (e) {
      /* custom elements: no table rows */
    }
    cards.push({
      title: "Density (rule of mixtures)",
      symbol: "ρ",
      value: density === null ? "n/a" : num(density, 3),
      units: density === null ? "no mass or molar-volume row for an element" : "g/cm³, ignores excess mixing volume",
    });
    var cost = null;
    if (breakdown) {
      cost = 0;
      Object.keys(breakdown).forEach(function (el) {
        cost += breakdown[el].contribution_usd_per_kg;
      });
    }
    cards.push({
      title: "Raw-material cost",
      symbol: "$/kg",
      value: cost === null ? "n/a" : num(cost, cost < 100 ? 2 : 0),
      units: cost === null ? "no price row for an element" : "USD/kg, prices as of " + core.PRICE_ASOF + ", indicative only",
    });
    $("predict-tier-a").innerHTML = cards
      .map(function (card) {
        return (
          '<div class="result-card result-card-compact"><h3>' + esc(card.title) + '</h3><div class="symbol">' + esc(card.symbol) +
          "</div><p>" + esc(card.value) + '</p><div class="units">' + esc(card.units) + "</div></div>"
        );
      })
      .join("");
    $("predict-cost-details").hidden = !breakdown;
    if (breakdown) {
      $("predict-cost-breakdown").innerHTML =
        '<div class="table-wrap"><table class="data feature-table"><thead><tr><th>Element</th><th class="num">Mass fraction</th>' +
        '<th class="num">USD/kg</th><th class="num">Contribution</th><th>Price basis</th><th>Source</th></tr></thead><tbody>' +
        Object.keys(breakdown)
          .map(function (el) {
            var row = breakdown[el];
            return (
              "<tr><td>" + esc(el) + '</td><td class="num">' + num(row.mass_fraction, 3) + '</td><td class="num">' + num(row.usd_per_kg, row.usd_per_kg < 100 ? 2 : 0) +
              '</td><td class="num">' + num(row.contribution_usd_per_kg, 2) + "</td><td>" + esc(row.basis) + " (" + esc(row.asof) + ")</td><td>" + esc(row.source) + "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table></div>" +
        '<p class="feature-note">Prices the elements going in, not melting, processing, yield losses or research-quantity purchasing, which dominate real cost at lab scale.</p>';
    }
  }

  function predictControls() {
    var options = ['<option value="">all routes, pooled</option>'];
    predict.processing.forEach(function (route) {
      options.push('<option value="' + esc(route.name) + '">' + esc(route.name.toLowerCase()) + " only (" + route.n + " alloys)</option>");
    });
    return (
      '<div class="feature-controls">' +
      '<label for="predict-alpha">Confidence</label><select id="predict-alpha"><option value="0.2">80%</option><option value="0.1" selected>90%</option><option value="0.05">95%</option></select>' +
      '<label for="predict-processing">Hardness training data</label><select id="predict-processing">' + options.join("") + "</select>" +
      "</div>"
    );
  }

  function probabilityBars(probabilities, set) {
    return Object.keys(probabilities)
      .sort(function (a, b) {
        return probabilities[b] - probabilities[a];
      })
      .map(function (label) {
        var p = probabilities[label];
        return (
          '<div class="predict-prob"><span class="feature-chip' + (set.indexOf(label) >= 0 ? "" : " is-out") + '">' + esc(label) +
          '</span><span class="feature-bar__track"><span class="feature-bar__fill" style="width:' + (100 * p).toFixed(1) +
          '%"></span></span><span class="feature-bar__n">' + pct(p, 0) + "</span></div>"
        );
      })
      .join("");
  }

  function phaseCard(title, result) {
    if (result.error) return '<div class="predict-card"><h3>' + esc(title) + "</h3>" + errorHtml(result.error) + "</div>";
    var set = result.prediction_set;
    var verdict = set.length === 0 ? "no label" : set.join(" or ");
    return (
      '<div class="predict-card"><h3>' + esc(title) + "</h3>" +
      '<div class="predict-card__value" style="font-size:17px">' + esc(verdict) + "</div>" +
      '<p class="feature-note">Prediction set at ' + pct(result.target_coverage, 0) + " confidence: the labels the model cannot rule out. Probabilities:</p>" +
      probabilityBars(result.probabilities, set) +
      (result.warnings.length ? "<ul>" + result.warnings.map(function (w) { return "<li>" + esc(w) + "</li>"; }).join("") + "</ul>" : "") +
      '<p class="feature-note">Random forest on the 14 descriptors, ' + int(result.n_training) + " training and " + int(result.n_calibration) +
      " calibration alloys from corpus v" + esc(result.corpus_version) + ". Coverage on unseen alloy systems is measured in the Benchmark view.</p></div>"
    );
  }

  // The library words some warnings for Python callers; say the same thing
  // in terms of this page's controls.
  function appWording(warning) {
    if (/^training data pools multiple processing routes/.test(warning)) {
      return (
        "The training data mixes processing routes (cast, annealed, powder and more). To use one route only, " +
        "choose it under Hardness training data above, at the cost of fewer training alloys."
      );
    }
    return warning;
  }

  function hardnessCard(entry) {
    if (!entry || entry.error) {
      return '<div class="predict-card"><h3>Vickers hardness</h3>' + errorHtml(entry ? entry.error : "not computed") + "</div>";
    }
    var low = entry.interval ? entry.interval[0] : null;
    var high = entry.interval ? entry.interval[1] : null;
    var clipped = low !== null && low < 0;
    return (
      '<div class="predict-card"><h3>Vickers hardness</h3>' +
      '<div class="predict-card__value">' + num(entry.value, 0) + "<small>HV</small></div>" +
      '<p class="feature-note">' + pct(1 - entry.alpha, 0) + " interval: " + (clipped ? "0" : num(low, 0)) + " to " + num(high, 0) + " HV" +
      (clipped ? " (the symmetric interval's lower end falls below zero)" : "") + ". " +
      (entry.in_domain ? "Inside" : "Outside") + " the hardness training data (" + int(entry.n_training) + " Borg alloys).</p>" +
      (entry.warnings.length ? "<ul>" + entry.warnings.map(function (w) { return "<li>" + esc(appWording(w)) + "</li>"; }).join("") + "</ul>" : "") +
      '<p class="feature-note">A screening estimate from a random forest with a conformal interval. It tells soft alloys from hard ones, ' +
      "but it cannot rank alloys whose estimates differ by less than the interval. Its measured error is in the " +
      '<a href="https://github.com/dfieser/hea-bench/blob/main/docs/property-hardness.md" target="_blank" rel="noopener">hardness model card</a>.</p></div>'
    );
  }

  function domainCard(result) {
    if (result.error) return '<div class="predict-card"><h3>Resembles the dataset?</h3>' + errorHtml(result.error) + "</div>";
    return (
      '<div class="predict-card"><h3>Resembles the dataset?</h3>' +
      '<div class="predict-card__value" style="font-size:17px">' + (result.in_domain ? "yes" : "no") + "</div><ul>" +
      "<li>" + (result.element_coverage ? "every element is covered by the data tables" : "an element is outside the data tables") + "</li>" +
      "<li>" + (result.element_set_seen ? "this alloy system appears " + int(result.family_count) + " times in the dataset" : "this alloy system is not in the dataset") + "</li>" +
      "<li>nearest studied system differs by " + num(result.nearest_family_distance, 2) + " in element-set (Jaccard) distance, limit " + num(result.family_distance_threshold, 2) + "</li>" +
      "<li>descriptor distance " + num(result.descriptor_distance, 2) + ", limit " + num(result.descriptor_distance_threshold, 2) + "</li>" +
      '</ul><p class="feature-note">Predictions are least reliable for alloys unlike the data they were fitted on.</p></div>'
    );
  }

  function runPredictions() {
    if (!predict.comp || !predict.started) return;
    if (predict.running) {
      predict.rerun = true;
      return;
    }
    predict.running = true;
    var comp = predict.comp;
    var host = $("predict-engine");
    var alphaEl = $("predict-alpha");
    var processingEl = $("predict-processing");
    var alpha = alphaEl ? parseFloat(alphaEl.value) : 0.1;
    var processing = processingEl && processingEl.value ? processingEl.value : null;
    var results = {};
    var unknown = Object.keys(comp).filter(function (el) {
      return !core.ELEMENT_DATA[el];
    });
    var finish = function () {
      predict.running = false;
      if (predict.rerun) {
        predict.rerun = false;
        runPredictions();
      }
    };
    if (unknown.length) {
      host.innerHTML = '<p class="feature-note">Not available for custom elements (' + esc(unknown.join(", ")) + "): the models need tabulated data for every element.</p>";
      finish();
      return;
    }
    predictGate
      .ensure()
      .then(function () {
        if (!predict.processing.length) {
          var info = engine.status().info || {};
          var routes = info.hardness_processing || {};
          predict.processing = Object.keys(routes)
            .filter(function (name) {
              return routes[name] >= HARDNESS_MIN_ROWS;
            })
            .map(function (name) {
              return { name: name, n: routes[name] };
            });
        }
        if (!$("predict-alpha")) {
          host.innerHTML = predictControls() + '<div class="predict-grid" id="predict-cards"></div>';
          $("predict-alpha").value = String(alpha);
          $("predict-alpha").addEventListener("change", runPredictions);
          $("predict-processing").addEventListener("change", runPredictions);
        }
        var settle = function (promise) {
          return promise.then(
            function (value) {
              return value;
            },
            function (error) {
              if (error.message === "Stopped.") throw error;
              return { error: error.message };
            }
          );
        };
        return predictGate.run("Predicting", function (progress) {
          return settle(engine.call("properties", { composition: comp, alpha: alpha, processing: processing, names: ["hardness"] }, progress))
            .then(function (r) {
              results.hardness = r.error ? r : r.properties.hardness;
              return settle(engine.call("phase_prediction", { composition: comp, task: "single_vs_multi", alpha: alpha }, progress));
            })
            .then(function (r) {
              results.binary = r;
              return settle(engine.call("phase_prediction", { composition: comp, task: "phase4", alpha: alpha }, progress));
            })
            .then(function (r) {
              results.phase4 = r;
              return settle(engine.call("applicability", { composition: comp }, progress));
            })
            .then(function (r) {
              results.domain = r;
            });
        });
      })
      .then(
        function () {
          if (predict.comp !== comp) return;
          $("predict-cards").innerHTML =
            phaseCard("Single-phase solid solution?", results.binary) +
            phaseCard("Structure", results.phase4) +
            hardnessCard(results.hardness) +
            domainCard(results.domain);
        },
        function () {
          /* the gate shows the error */
        }
      )
      .then(finish, finish);
  }

  document.addEventListener("hea:alloy-result", function (event) {
    var payload = event.detail;
    var panel = $("predict-panel");
    if (!payload || !payload.composition) {
      panel.classList.add("hidden");
      predict.comp = null;
      return;
    }
    panel.classList.remove("hidden");
    predict.comp = payload.composition;
    tierACards(payload.composition);
    if (!predict.started && autostart() && engine.available()) predict.started = true;
    if (predict.started) runPredictions();
  });

  // ------------------------------------- calculator: Omega pair-table check
  //
  // core.omegaSensitivity is the browser port of the MCP omega_sensitivity
  // tool (parity: tests/test_web_properties_parity.py). It runs on the
  // composition and pair values the calculator just used.

  var omegaInput = { comp: null, options: null };

  function renderOmega() {
    var panel = $("omega-panel");
    var out = $("omega-sensitivity");
    if (!omegaInput.comp || Object.keys(omegaInput.comp).length < 2) {
      panel.classList.add("hidden");
      return;
    }
    panel.classList.remove("hidden");
    var shift = Number($("omega-perturbation").value);
    if (!(shift >= 0)) {
      out.innerHTML = errorHtml("Enter a shift of zero or more kJ/mol.");
      return;
    }
    var r;
    try {
      r = core.omegaSensitivity(omegaInput.comp, shift, omegaInput.options);
    } catch (error) {
      out.innerHTML = '<p class="feature-note">Not available for this composition: ' + esc(error.message) + ".</p>";
      return;
    }
    var threshold = core.YANG_OMEGA_THRESHOLD;
    var ends = r.omega_at_range_endpoints;
    var low = ends.length ? Math.min.apply(null, ends) : null;
    var high = ends.length ? Math.max.apply(null, ends) : null;
    // An endpoint exactly at zero drops out of the list: Omega is unbounded there too.
    var unbounded = r.diverges_within_range || ends.length < 2;
    var range = low === null ? "unbounded" : unbounded ? num(low, 2) + " to unbounded" : num(low, 2) + " to " + num(high, 2);
    // What to trust, in plain words: the Omega number, and the Omega >= 1.1
    // side of Yang's rule, each either survive the shift or they do not.
    var verdict;
    if (low === null) {
      verdict = "<b>ΔH<sub>mix</sub> is exactly zero here, so Ω is unbounded.</b> Use a shift above zero to see the range around it.";
    } else if (unbounded) {
      verdict =
        "<b>The Ω number is not robust here.</b> The shifted ΔH<sub>mix</sub> range includes zero, so across the " +
        "spread of published pair tables Ω can be anything from " + num(low, 2) + " upward.";
      verdict +=
        low >= threshold
          ? " <b>The verdict is robust:</b> Ω stays at or above Yang's 1.1 threshold throughout, so trust the rule's verdict, not the Ω number."
          : " Ω also drops below Yang's 1.1 threshold within that range, so at this shift neither the Ω number nor its Ω ≥ 1.1 verdict should be trusted.";
    } else {
      verdict = "<b>Ω stays between " + num(low, 2) + " and " + num(high, 2) + "</b> across the shift.";
      if (low >= threshold) {
        verdict += " That is above Yang's 1.1 threshold throughout, so the Ω ≥ 1.1 verdict does not depend on the pair table.";
      } else if (high < threshold) {
        verdict += " That is below Yang's 1.1 threshold throughout, so the Ω < 1.1 verdict does not depend on the pair table.";
      } else {
        verdict += " Yang's 1.1 threshold falls inside that range, so the Ω ≥ 1.1 verdict depends on which pair table is used.";
      }
    }
    out.innerHTML =
      stats([
        [num(r.h_mix_kj_mol, 2), "ΔHmix as computed (kJ/mol)"],
        [r.omega === null ? "unbounded" : num(r.omega, 2), "Ω as computed"],
        [r.dominant_element, "element that dominates ΔHmix"],
        [num(r.h_mix_range_kj_mol[0], 2) + " to " + num(r.h_mix_range_kj_mol[1], 2), "ΔHmix after the shift (kJ/mol)"],
        [range, "Ω over that range"],
      ]) +
      '<p class="feature-note">' + verdict + "</p>" +
      '<details class="feature-details"><summary>Pair contributions to ΔHmix</summary>' +
      '<div class="table-wrap"><table class="data feature-table"><thead><tr><th>Pair</th><th class="num">H<sub>ij</sub> (kJ/mol)</th>' +
      '<th class="num">4c<sub>i</sub>c<sub>j</sub></th><th class="num">Contribution (kJ/mol)</th></tr></thead><tbody>' +
      r.pair_contributions
        .map(function (c) {
          return (
            "<tr><td>" + esc(c.pair) + '</td><td class="num">' + num(c.pair_enthalpy_kj_mol, 1) + '</td><td class="num">' +
            num(c.weight, 4) + '</td><td class="num">' + signed(c.contribution_kj_mol, 3) + "</td></tr>"
          );
        })
        .join("") +
      "</tbody></table></div></details>";
  }

  document.addEventListener("hea:alloy-result", function (event) {
    var payload = event.detail;
    omegaInput.comp = payload && payload.composition ? payload.composition : null;
    omegaInput.options = payload && payload.coreOptions ? payload.coreOptions : null;
    renderOmega();
  });
  $("omega-perturbation").addEventListener("input", renderOmega);

  // --------------------------------------------------------------- ceramics

  var CERAMIC_EXAMPLES = {
    carbide5: { structure: "rock_salt_carbide", metals: "HfNbTaTiZr" },
    nitride5: { structure: "rock_salt_nitride", metals: "TiZrHfVNb" },
    diboride5: { structure: "diboride", metals: "HfZrTaNbTi" },
  };
  var CERAMIC_DESCRIBE = {
    rock_salt_carbide: core.describeRockSaltCarbide,
    rock_salt_nitride: core.describeRockSaltNitride,
    diboride: core.describeDiboride,
  };
  var lastCeramic = null;

  function vecLine(vec, points) {
    var lo = 7.5;
    var hi = 10.5;
    var x = function (v) {
      return 20 + ((Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo)) * 520;
    };
    var marks = points
      .map(function (p, i) {
        return (
          '<line x1="' + x(p.value) + '" x2="' + x(p.value) + '" y1="22" y2="44" class="axis" stroke-dasharray="3 3"/>' +
          '<text x="' + x(p.value) + '" y="' + (i % 2 ? 60 : 16) + '" text-anchor="middle" class="label">' + p.value + "</text>"
        );
      })
      .join("");
    var dot = vec === null ? "" : '<circle cx="' + x(vec) + '" cy="33" r="6" class="pt-front"/>';
    return (
      '<div class="ceramic-vec-line feature-plot"><svg viewBox="0 0 560 66" role="img" aria-label="VEC against the literature reference points">' +
      '<line x1="20" x2="540" y1="33" y2="33" class="axis"/>' + marks + dot + "</svg></div>"
    );
  }

  function renderCeramic(report) {
    var e = report.entropy;
    var cards = [
      { title: "Configurational entropy, per mole of cations", symbol: "ΔS conf", value: num(e.per_mole_cation_j_mol_k, 3), units: "J/mol·K (" + num(e.per_mole_cation_r_units, 4) + " R), equals per formula unit" },
      { title: "Configurational entropy, per mole of atoms", symbol: "ΔS conf", value: num(e.per_mole_atoms_j_mol_k, 3), units: "J/mol·K" },
      { title: "Metals on the sublattice", symbol: "n", value: String(report.n_metals), units: "anion: " + report.anion },
    ];
    if (report.vec_per_formula_unit !== undefined) {
      cards.push({ title: "Valence electron concentration", symbol: "VEC", value: num(report.vec_per_formula_unit, 3), units: "per formula unit, metal plus anion electrons" });
    }
    var html =
      '<div class="results results-compact">' +
      cards
        .map(function (c) {
          return '<div class="result-card result-card-compact"><h3>' + esc(c.title) + '</h3><div class="symbol">' + esc(c.symbol) + "</div><p>" + esc(c.value) + '</p><div class="units">' + esc(c.units) + "</div></div>";
        })
        .join("") +
      "</div>";
    if (report.vec_reference_points) {
      html +=
        '<div class="feature-subhead">VEC against the literature reference points</div>' +
        vecLine(report.vec_per_formula_unit, report.vec_reference_points) +
        "<ul class=\"feature-note\">" +
        report.vec_reference_points
          .map(function (p) {
            return "<li>" + p.value + ": " + esc(p.marks) + " (" + esc(p.source) + ")</li>";
          })
          .join("") +
        "</ul>";
    } else {
      html += '<p class="feature-note">VEC reference points from the rock-salt literature do not transfer to the AlB₂ structure, so the diboride report carries entropy only.</p>';
    }
    html +=
      '<p class="feature-note">' + esc(e.note) + "</p>" +
      '<details class="feature-details"><summary>What is deliberately absent</summary><ul class="feature-note">' +
      report.notes.map(function (n) { return "<li>" + esc(n) + "</li>"; }).join("") + "</ul></details>" +
      '<details class="feature-details"><summary>Sources</summary><ul class="feature-note">' +
      Object.keys(report.sources).map(function (k) { return "<li><b>" + esc(k) + "</b>: " + esc(report.sources[k]) + "</li>"; }).join("") +
      "</ul></details>";
    $("ceramic-results").innerHTML = html;
    var warnings = $("warnings");
    if (warnings) warnings.innerHTML = report.warnings.map(function (w) { return "<li>" + esc(w) + "</li>"; }).join("");
  }

  function ceramicCalculate() {
    var errorEl = $("error");
    try {
      var metals = parseFormula($("ceramic-metals").value);
      var report = CERAMIC_DESCRIBE[$("ceramic-structure").value](metals);
      lastCeramic = report;
      if (errorEl) {
        errorEl.textContent = "";
        errorEl.classList.add("hidden");
      }
      renderCeramic(report);
    } catch (error) {
      if (errorEl) {
        errorEl.textContent = error.message;
        errorEl.classList.remove("hidden");
      }
    }
  }

  function loadCeramicExample(key) {
    var example = CERAMIC_EXAMPLES[key];
    if (!example) return;
    $("ceramic-structure").value = example.structure;
    $("ceramic-metals").value = example.metals;
    ceramicCalculate();
  }

  $("ceramic-calculate").addEventListener("click", ceramicCalculate);
  $("ceramic-metals").addEventListener("keydown", function (event) {
    if (event.key === "Enter") ceramicCalculate();
  });
  $("ceramic-example").addEventListener("change", function () {
    loadCeramicExample(this.value);
    this.value = "";
  });
  $("ceramic-empty-example").addEventListener("click", function () {
    loadCeramicExample("carbide5");
  });
  $("ceramic-copy-json").addEventListener("click", function () {
    if (!lastCeramic) return;
    navigator.clipboard.writeText(JSON.stringify(lastCeramic, null, 2)).then(
      function () {
        $("ceramic-copy-message").textContent = "Copied.";
        setTimeout(function () {
          $("ceramic-copy-message").textContent = "";
        }, 1500);
      },
      function () {
        $("ceramic-copy-message").textContent = "Copy failed.";
      }
    );
  });

  // ---------------------------------------------------------------- dataset

  var dataset = { offset: 0, limit: 50, filters: {}, total: 0, loaded: null };
  var datasetGate = new Gate($("dataset-gate"), {
    what: "The consolidated alloy dataset.",
    needsCorpus: true,
    version: function () {
      return $("dataset-version").value;
    },
    onReady: function () {
      loadDataset(true);
    },
  }).bind();

  function bars(title, counts, keepOrder) {
    var keys = Object.keys(counts);
    if (!keepOrder) {
      keys.sort(function (a, b) {
        return counts[b] - counts[a];
      });
    }
    var max = Math.max.apply(null, keys.map(function (k) { return counts[k]; }).concat([1]));
    return (
      '<div class="feature-bars"><div class="feature-bars__title">' + esc(title) + "</div>" +
      keys
        .map(function (k) {
          return (
            '<div class="feature-bar"><span>' + esc(k) + '</span><span class="feature-bar__track"><span class="feature-bar__fill" style="width:' +
            ((100 * counts[k]) / max).toFixed(1) + '%"></span></span><span class="feature-bar__n">' + int(counts[k]) + "</span></div>"
          );
        })
        .join("") +
      "</div>"
    );
  }

  function stats(items) {
    return (
      '<div class="feature-stats">' +
      items
        .map(function (item) {
          return '<div class="feature-stat"><span class="feature-stat__value">' + esc(item[0]) + '</span><span class="feature-stat__label">' + esc(item[1]) + "</span></div>";
        })
        .join("") +
      "</div>"
    );
  }

  function datasetFilters() {
    var form = $("dataset-filters");
    var get = function (name) {
      return form.elements[name].value.trim();
    };
    var filters = {};
    if (get("contains")) filters.contains = elementsList(get("contains"));
    if (get("excludes")) filters.excludes = elementsList(get("excludes"));
    if (get("exact")) filters.elements = elementsList(get("exact"));
    if (get("n_elements_min")) filters.n_elements_min = parseInt(get("n_elements_min"), 10);
    if (get("n_elements_max")) filters.n_elements_max = parseInt(get("n_elements_max"), 10);
    if (get("phase")) filters.phase = get("phase");
    if (get("source")) filters.source = get("source");
    if (get("has_conflict")) filters.has_conflict = get("has_conflict") === "true";
    return filters;
  }

  function renderDatasetSummary(d, version) {
    var by = d.by_n_elements || {};
    var byN = {};
    Object.keys(by)
      .sort(function (a, b) {
        return a - b;
      })
      .forEach(function (k) {
        byN[k + (k === "1" ? " element" : " elements")] = by[k];
      });
    var sourceNames = { borg2020: "Borg 2020", pei2020: "Pei 2020", peivaste: "Peivaste 2023", chizhevskiy2026: "Chizhevskiy 2026" };
    var bySource = {};
    Object.keys(d.by_source || {}).forEach(function (k) {
      bySource[sourceNames[k] || k] = d.by_source[k];
    });
    $("dataset-summary").innerHTML =
      stats([
        [int(d.n_rows), "unique compositions"],
        [int(d.n_labelled), "with a consensus phase"],
        [int(d.n_conflicts), "where sources disagree"],
        [int(d.n_families), "alloy systems"],
        [d.multi_source_agreement_rate === null ? "n/a" : pct(d.multi_source_agreement_rate), "agreement where sources overlap"],
      ]) +
      '<p class="feature-note">Corpus v' + esc(version) + (Object.keys(dataset.filters).length ? ", filtered." : ", all rows.") + "</p>" +
      bars("Consensus phase", d.by_phase || {}) +
      bars("Contributing source", bySource) +
      bars("Elements per alloy", byN, true);
  }

  function datasetRow(row, index) {
    var phase = row.has_conflict ? '<span class="feature-badge is-warn">conflict</span>' : esc(row.canonical_phase || "");
    return (
      '<tr class="is-clickable" data-row="' + index + '"><td class="comp">' + compHtml(row.composition) + "</td><td>" + row.n_elements + "</td><td>" + phase +
      "</td><td>" + esc(row.sources.join(", ")) + "</td><td>" + esc(row.processing || "") +
      "</td><td>" + calculatorButton(row.composition, index) + "</td></tr>"
    );
  }

  // The calculator covers its element table only; say so instead of failing.
  function calculatorButton(comp, index) {
    var outside = Object.keys(comp).filter(function (el) {
      return !core.ELEMENT_DATA[el];
    });
    return outside.length
      ? '<button type="button" class="ghost" disabled title="' + esc(outside.join(", ")) + ' outside the calculator element table">Calculator</button>'
      : '<button type="button" class="ghost" data-open="' + index + '">Calculator</button>';
  }

  function datasetDetail(row) {
    var items = [];
    Object.keys(row.labels).forEach(function (source) {
      items.push([source + " label", row.labels[source] + (row.raw_labels[source] ? ' (published as "' + row.raw_labels[source] + '")' : "")]);
    });
    Object.keys(row.source_row_ids).forEach(function (source) {
      items.push([source + " record", row.source_row_ids[source]]);
    });
    items.push(["Composition key", row.composition_key]);
    items.push(["Alloy system", row.family]);
    items.push(["All descriptors computable", row.descriptor_ready ? "yes" : "no"]);
    var doi = row.doi ? '<a href="https://doi.org/' + esc(row.doi) + '" target="_blank" rel="noopener">' + esc(row.doi) + "</a>" : null;
    return (
      '<dl class="feature-detail">' +
      items.map(function (item) { return "<div><dt>" + esc(item[0]) + "</dt><dd>" + esc(item[1]) + "</dd></div>"; }).join("") +
      (doi ? "<div><dt>Paper</dt><dd>" + doi + "</dd></div>" : "") +
      "</dl>"
    );
  }

  function loadDataset(withSummary) {
    var version = $("dataset-version").value;
    var tbody = $("dataset-tbody");
    datasetGate
      .ensure()
      .then(function () {
        return datasetGate.run("Reading the dataset", function (progress) {
          var steps = [];
          if (withSummary) {
            steps.push(
              engine.call("dataset_describe", { filters: dataset.filters, version: version }, progress).then(function (d) {
                renderDatasetSummary(d, version);
              })
            );
          }
          steps.push(
            engine.call("dataset_query", { filters: dataset.filters, version: version, offset: dataset.offset, limit: dataset.limit }, progress).then(function (page) {
              dataset.total = page.n_matching;
              dataset.loaded = page.rows;
              tbody.innerHTML = page.rows.length
                ? page.rows.map(datasetRow).join("")
                : '<tr><td colspan="6">No alloy matches these filters.</td></tr>';
              var last = Math.min(dataset.offset + dataset.limit, dataset.total);
              $("dataset-count").textContent = dataset.total
                ? "Rows " + int(dataset.offset + 1) + " to " + int(last) + " of " + int(dataset.total)
                : "No rows";
              $("dataset-prev").disabled = dataset.offset === 0;
              $("dataset-next").disabled = last >= dataset.total;
            })
          );
          return Promise.all(steps);
        });
      })
      .catch(function (error) {
        if (datasetGate.error) return;
        $("dataset-summary").innerHTML = errorHtml(error);
      });
  }

  $("dataset-filters").addEventListener("submit", function (event) {
    event.preventDefault();
    dataset.filters = datasetFilters();
    dataset.offset = 0;
    loadDataset(true);
  });
  $("dataset-filters").addEventListener("reset", function () {
    setTimeout(function () {
      dataset.filters = {};
      dataset.offset = 0;
      if (isBuilt($("dataset-version").value)) loadDataset(true);
    }, 0);
  });
  $("dataset-version").addEventListener("change", function () {
    dataset.offset = 0;
    loadDataset(true);
  });
  $("dataset-prev").addEventListener("click", function () {
    dataset.offset = Math.max(0, dataset.offset - dataset.limit);
    loadDataset(false);
  });
  $("dataset-next").addEventListener("click", function () {
    dataset.offset += dataset.limit;
    loadDataset(false);
  });
  $("dataset-tbody").addEventListener("click", function (event) {
    var open = event.target.closest("[data-open]");
    if (open) {
      openInCalculator(dataset.loaded[Number(open.getAttribute("data-open"))].composition);
      return;
    }
    var tr = event.target.closest("tr[data-row]");
    if (!tr || !dataset.loaded) return;
    var next = tr.nextElementSibling;
    if (next && next.classList.contains("feature-detail-row")) {
      next.remove();
      tr.classList.remove("is-open");
      return;
    }
    var row = dataset.loaded[Number(tr.getAttribute("data-row"))];
    var detail = document.createElement("tr");
    detail.className = "feature-detail-row";
    detail.innerHTML = '<td colspan="6">' + datasetDetail(row) + "</td>";
    tr.after(detail);
    tr.classList.add("is-open");
  });
  $("dataset-download").addEventListener("click", function () {
    var version = $("dataset-version").value;
    datasetGate
      .ensure()
      .then(function () {
        return engine.call("dataset_csv", { filters: dataset.filters, version: version });
      })
      .then(function (r) {
        download(r.filename, r.text, "text/csv");
      })
      .catch(function (error) {
        $("dataset-summary").insertAdjacentHTML("afterbegin", errorHtml(error));
      });
  });
  onShow("dataset", function () {
    if (!dataset.loaded && autostart() && engine.available()) loadDataset(true);
  });

  // ------------------------------------------ dataset: measured properties

  var measured = { rows: null, prop: "hardness", unit: "" };
  var measuredGate = new Gate($("measured-gate"), {
    what: "Measured hardness and density.",
    onReady: function () {
      loadMeasured();
    },
  }).bind();

  function measuredRow(row, index) {
    var density = measured.prop === "density";
    var cells = [
      '<td class="comp">' + compHtml(row.composition) + "</td>",
      '<td class="num">' + num(row.value, density ? 2 : 0) + "</td>",
    ];
    if (density) {
      var estimate = core.tierADensity(row.composition);
      cells.push(
        '<td class="num">' +
          (estimate === null ? "n/a" : num(estimate, 2) + " (" + signed((100 * (estimate - row.value)) / row.value, 1) + "%)") +
          "</td>"
      );
    }
    cells.push("<td>" + esc(row.processing || "not stated") + "</td>");
    cells.push("<td>" + esc(row.year || "") + "</td>");
    cells.push(
      "<td>" + (row.doi ? '<a href="https://doi.org/' + esc(row.doi) + '" target="_blank" rel="noopener">' + esc(row.doi) + "</a>" : "") + "</td>"
    );
    cells.push("<td>" + calculatorButton(row.composition, index) + "</td>");
    return "<tr>" + cells.join("") + "</tr>";
  }

  function renderMeasured(r, contains) {
    var density = r.property === "density";
    $("measured-thead").innerHTML =
      '<tr><th>Composition</th><th class="num">Measured (' + esc(density ? "g/cm³" : r.unit) + ")</th>" +
      (density ? '<th class="num">Instant estimate (difference)</th>' : "") +
      "<th>Processing</th><th>Year</th><th>Paper</th><th></th></tr>";
    $("measured-tbody").innerHTML = r.rows.length
      ? r.rows.map(measuredRow).join("")
      : '<tr><td colspan="7">No measured alloy contains all of these elements.</td></tr>';
    var what = density ? "measured densities" : "room-temperature hardness measurements";
    var note =
      (contains.length
        ? int(r.n_matching) + " of " + int(r.n_total) + " " + what + " are for alloys containing " + esc(contains.join(", ")) + "."
        : int(r.n_total) + " " + what + ".") +
      " Source: " + esc(r.source) + ".";
    if (density) {
      var diffs = r.rows
        .map(function (row) {
          var estimate = core.tierADensity(row.composition);
          return estimate === null ? null : Math.abs(estimate - row.value) / row.value;
        })
        .filter(function (d) {
          return d !== null;
        });
      if (diffs.length) {
        note +=
          " On these rows the instant rule-of-mixtures estimate differs from the measurement by " +
          pct(
            diffs.reduce(function (a, b) {
              return a + b;
            }, 0) / diffs.length
          ) +
          " on average.";
      }
    }
    $("measured-summary").innerHTML = '<p class="feature-note">' + note + "</p>";
  }

  function loadMeasured() {
    var prop = $("measured-property").value;
    var contains = elementsList($("measured-contains").value);
    measuredGate
      .ensure()
      .then(function () {
        return measuredGate.run("Reading the measurements", function (progress) {
          return engine.call("measured_properties", { prop: prop, contains: contains }, progress);
        });
      })
      .then(function (r) {
        measured.rows = r.rows;
        measured.prop = r.property;
        measured.unit = r.unit;
        renderMeasured(r, contains);
      })
      .catch(function (error) {
        if (measuredGate.error) return;
        $("measured-summary").innerHTML = errorHtml(error);
      });
  }

  function csvCell(value) {
    var text = value === null || value === undefined ? "" : String(value);
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  }

  $("measured-filters").addEventListener("submit", function (event) {
    event.preventDefault();
    loadMeasured();
  });
  $("measured-property").addEventListener("change", loadMeasured);
  $("measured-tbody").addEventListener("click", function (event) {
    var open = event.target.closest("[data-open]");
    if (open && measured.rows) openInCalculator(measured.rows[Number(open.getAttribute("data-open"))].composition);
  });
  $("measured-download").addEventListener("click", function () {
    if (!measured.rows) {
      loadMeasured();
      return;
    }
    var header = ["formula_as_published", "composition", "value", "unit", "processing", "year", "doi", "borg_reference_id"];
    var lines = [header.join(",")].concat(
      measured.rows.map(function (row) {
        return [row.formula_raw, compText(row.composition), row.value, measured.unit, row.processing, row.year, row.doi, row.reference_id]
          .map(csvCell)
          .join(",");
      })
    );
    download("hea-bench-measured-" + measured.prop + ".csv", lines.join("\r\n") + "\r\n", "text/csv");
  });
  onShow("dataset", function () {
    if (!measured.rows && autostart() && engine.available()) loadMeasured();
  });

  // -------------------------------------------------------------- benchmark

  var bench = { summary: null };
  var benchmarkGate = new Gate($("benchmark-gate"), {
    what: "The benchmark, live.",
    needsCorpus: true,
    version: function () {
      return $("benchmark-version").value;
    },
    onReady: function () {
      loadBenchmark();
    },
  }).bind();

  function benchArgs() {
    return { task: $("benchmark-task").value, version: $("benchmark-version").value };
  }

  function metricCell(scheme, name) {
    return num(scheme[name + "_mean"], 3) + ' <span class="feature-note">± ' + num(scheme[name + "_se"], 3) + "</span>";
  }

  function renderSplits(s) {
    var d = s.described;
    var o = d.family_overlap_profile;
    var digest = function (name) {
      var r = s.digests[name];
      return (
        "<tr><td>" + (name === "grouped" ? "Family-grouped (extrapolation)" : "Random (interpolation)") + '</td><td class="comp">' + esc(r.computed.slice(0, 16)) + "…</td><td>" +
        (r.frozen === null
          ? '<span class="feature-badge">no frozen digest</span>'
          : r.match
          ? '<span class="feature-badge is-good">matches the frozen split</span>'
          : '<span class="feature-badge is-warn">differs from the frozen split</span>') +
        '</td><td class="num">' + d[name].rows_per_fold.join(" / ") + "</td></tr>"
      );
    };
    $("benchmark-splits-body").innerHTML =
      stats([
        [int(d.n_rows), "alloys with a consensus label"],
        [int(s.n_evaluated), "with every descriptor finite (scored)"],
        [int(o.n_families), "alloy systems"],
        [pct(o.random_fraction_rows_interpolable), "of rows share a system across a random-split boundary"],
      ]) +
      "<p>Under the random split, " + int(o.random_straddling_families) + " alloy systems appear on both sides of a fold boundary, covering " +
      int(o.random_rows_in_straddling_families) + " rows. Under the family-grouped split that number is " + int(o.grouped_straddling_families) + " by construction.</p>" +
      '<div class="table-wrap"><table class="data feature-table"><caption>The fold assignment below was recomputed in this page and checked against the published digest.</caption>' +
      "<thead><tr><th>Split</th><th>Digest (SHA-256)</th><th>Check</th><th>Rows per fold</th></tr></thead><tbody>" +
      digest("grouped") + digest("random") + "</tbody></table></div>";
  }

  function baselineRow(name, published, live) {
    var cells = function (r) {
      return (
        '<td class="num">' + metricCell(r.grouped, "balanced_accuracy") + '</td><td class="num">' + metricCell(r.random, "balanced_accuracy") +
        '</td><td class="num">' + signed(r.gap.balanced_accuracy) +
        '</td><td class="num">' + num(r.grouped.macro_f1_mean, 3) + '</td><td class="num">' + num(r.random.macro_f1_mean, 3) + "</td>"
      );
    };
    var status = "";
    if (live && published) {
      var same = Math.abs(live.gap.balanced_accuracy - published.gap.balanced_accuracy) < 1e-9 &&
        Math.abs(live.grouped.balanced_accuracy_mean - published.grouped.balanced_accuracy_mean) < 1e-9;
      status = same ? '<span class="feature-badge is-good">reproduced here</span>' : '<span class="feature-badge is-warn">differs here</span>';
    } else if (live) {
      status = '<span class="feature-badge is-good">computed here</span>';
    }
    var shown = live || published;
    return (
      "<tr><td>" + esc(name) + "</td>" + (shown ? cells(shown) : '<td colspan="5" class="feature-note">not run yet</td>') +
      "<td>" + status + ' <button type="button" class="ghost" data-run="' + esc(name) + '">' + (live ? "Run again" : "Run here") + "</button></td></tr>"
    );
  }

  function renderBaselines() {
    var s = bench.summary;
    var published = {};
    ((s.published && s.published.results) || []).forEach(function (r) {
      published[r.model] = r;
    });
    bench.live = bench.live || {};
    $("benchmark-baselines-body").innerHTML =
      '<div class="table-wrap"><table class="data feature-table"><thead><tr><th>Model</th><th class="num">Grouped balanced accuracy</th><th class="num">Random balanced accuracy</th>' +
      '<th class="num">Gap</th><th class="num">Grouped macro F1</th><th class="num">Random macro F1</th><th></th></tr></thead><tbody>' +
      s.baselines.map(function (name) {
        return baselineRow(name, published[name], bench.live[name]);
      }).join("") +
      "</tbody></table></div>" +
      '<p class="feature-note">' + (s.published ? "Published values are from docs/benchmark-baselines.json; " : "No published table for this corpus version; ") +
      "± is the standard error over the five folds. The random forest takes about a minute here, gradient boosting several.</p>";
  }

  function loadBenchmark() {
    var args = benchArgs();
    benchmarkGate
      .ensure()
      .then(function () {
        return benchmarkGate.run("Loading the benchmark", function (progress) {
          return engine.call("benchmark_summary", args, progress);
        });
      })
      .then(function (s) {
        bench.summary = s;
        bench.live = {};
        renderSplits(s);
        renderBaselines();
      })
      .catch(function (error) {
        if (!benchmarkGate.error) $("benchmark-splits-body").innerHTML = errorHtml(error);
      });
  }

  $("benchmark-task").addEventListener("change", function () {
    $("benchmark-score-body").innerHTML = "";
    $("benchmark-coverage-body").innerHTML = "";
    if (bench.summary) loadBenchmark();
  });
  $("benchmark-version").addEventListener("change", function () {
    $("benchmark-score-body").innerHTML = "";
    $("benchmark-coverage-body").innerHTML = "";
    if (bench.summary) loadBenchmark();
  });
  $("benchmark-baselines-body").addEventListener("click", function (event) {
    var button = event.target.closest("[data-run]");
    if (!button) return;
    var model = button.getAttribute("data-run");
    var args = benchArgs();
    args.model = model;
    benchmarkGate
      .run("Scoring " + model, function (progress) {
        return engine.call("benchmark_run", args, progress);
      })
      .then(function (report) {
        bench.live[model] = report;
        renderBaselines();
      })
      .catch(function (error) {
        $("benchmark-baselines-body").insertAdjacentHTML("beforeend", errorHtml(error));
      });
  });
  $("benchmark-folds").addEventListener("click", function () {
    benchmarkGate
      .ensure()
      .then(function () {
        return engine.call("benchmark_folds_csv", benchArgs());
      })
      .then(function (r) {
        download(r.filename, r.text, "text/csv");
      })
      .catch(function (error) {
        $("benchmark-score-body").innerHTML = errorHtml(error);
      });
  });
  // An example upload: the most common label for every alloy under both
  // splits, so a first-time user sees the file format and the scoring
  // before training anything.
  $("benchmark-example").addEventListener("click", function () {
    benchmarkGate
      .ensure()
      .then(function () {
        return engine.call("benchmark_folds_csv", benchArgs());
      })
      .then(function (r) {
        var lines = r.text.replace(/\r/g, "").split("\n").filter(Boolean);
        var header = lines[0].split(",");
        var keyAt = header.indexOf("composition_key");
        var labelAt = header.indexOf("label");
        var counts = {};
        lines.slice(1).forEach(function (line) {
          var label = line.split(",")[labelAt];
          counts[label] = (counts[label] || 0) + 1;
        });
        var common = Object.keys(counts).sort(function (a, b) {
          return counts[b] - counts[a];
        })[0];
        var out = ["composition_key,grouped,random"].concat(
          lines.slice(1).map(function (line) {
            return line.split(",")[keyAt] + "," + common + "," + common;
          })
        );
        download(r.filename.replace("-folds.csv", "-example-predictions.csv"), out.join("\r\n") + "\r\n", "text/csv");
      })
      .catch(function (error) {
        $("benchmark-score-body").innerHTML = errorHtml(error);
      });
  });
  $("benchmark-upload").addEventListener("click", function () {
    $("benchmark-upload-file").click();
  });
  $("benchmark-upload-file").addEventListener("change", function () {
    var input = this;
    var name = input.files && input.files[0] ? input.files[0].name : "uploaded predictions";
    readFile(input)
      .then(function (text) {
        return benchmarkGate.ensure().then(function () {
          var args = benchArgs();
          args.csv_text = text;
          args.model_name = name;
          return benchmarkGate.run("Scoring your predictions", function (progress) {
            return engine.call("benchmark_score", args, progress);
          });
        });
      })
      .then(function (r) {
        $("benchmark-score-body").innerHTML =
          '<div class="table-wrap"><table class="data feature-table"><caption>' + esc(r.model) + ": " + int(r.n_rows_evaluated) +
          " alloys scored under both splits, corpus v" + esc(r.corpus_version) + ", task " + esc(r.task) + ".</caption>" +
          "<thead><tr><th>Metric</th><th class=\"num\">Grouped</th><th class=\"num\">Random</th><th class=\"num\">Gap</th></tr></thead><tbody>" +
          ["balanced_accuracy", "macro_f1", "mcc", "accuracy"]
            .map(function (m) {
              return "<tr><td>" + m.replace(/_/g, " ") + '</td><td class="num">' + metricCell(r.grouped, m) + '</td><td class="num">' + metricCell(r.random, m) +
                '</td><td class="num">' + signed(r.gap[m]) + "</td></tr>";
            })
            .join("") +
          "</tbody></table></div>";
      })
      .catch(function (error) {
        $("benchmark-score-body").innerHTML = errorHtml(error);
      });
  });
  $("benchmark-coverage-run").addEventListener("click", function () {
    var args = benchArgs();
    benchmarkGate
      .ensure()
      .then(function () {
        return benchmarkGate.run("Running the coverage study", function (progress) {
          return engine.call("coverage", args, progress);
        });
      })
      .then(function (study) {
        var groupNames = {
          all: "all alloys",
          in_domain: "flagged like the dataset",
          out_of_domain: "flagged unlike the dataset",
          fewer_than_four: "fewer than four elements",
          four_or_more: "four or more elements",
          four_or_more_one_element_from_training: "four or more, one element from a training system",
          four_or_more_farther: "four or more, farther from training",
        };
        var rows = [];
        study.levels.forEach(function (level) {
          Object.keys(groupNames).forEach(function (g) {
            var c = level.groups[g];
            if (!c || !c.n) return;
            rows.push(
              "<tr><td>" + pct(level.target, 0) + "</td><td>" + esc(groupNames[g]) + '</td><td class="num">' + int(c.n) + '</td><td class="num">' + num(c.coverage, 3) +
              (c.fold_se === null ? "" : ' <span class="feature-note">± ' + num(c.fold_se, 3) + "</span>") + '</td><td class="num">' + num(c.mean_set_size, 2) + "</td></tr>"
            );
          });
        });
        $("benchmark-coverage-body").innerHTML =
          '<div class="table-wrap"><table class="data feature-table"><caption>' + int(study.n_rows) + " alloys, " + int(study.n_out_of_domain) +
          " flagged unlike the dataset at test time across the five grouped folds. Coverage is the share of alloys whose set contains the true label.</caption>" +
          '<thead><tr><th>Target</th><th>Alloys</th><th class="num">n</th><th class="num">Coverage</th><th class="num">Mean set size</th></tr></thead><tbody>' +
          rows.join("") + "</tbody></table></div>" +
          '<p class="feature-note">A set can always reach its target by listing every label, so read coverage next to set size.</p>';
      })
      .catch(function (error) {
        $("benchmark-coverage-body").innerHTML = errorHtml(error);
      });
  });
  onShow("benchmark", function () {
    if (!bench.summary && autostart() && engine.available()) loadBenchmark();
  });

  // ------------------------------------------------------------ design: search

  var PROPERTIES = [
    ["hardness", "hardness (HV)"],
    ["density", "density (g/cm³)"],
    ["cost_per_kg", "raw-material cost (USD/kg)"],
    ["melting_temperature", "melting temperature (K)"],
  ];
  var RULES = [
    ["yang_omega", "Yang Ω", ["single-phase", "multi-phase"]],
    ["zhang_delta", "Zhang δ", ["single-phase", "multi-phase"]],
    ["guo_vec", "Guo VEC", ["FCC", "BCC", "mixed"]],
    ["king_phi", "King Φ", ["solid_solution", "intermetallic"]],
    ["ye_phi", "Ye φ", ["solid_solution", "intermetallic"]],
    ["senkov_kappa", "Senkov κ", ["solid_solution", "intermetallic"]],
    ["yeh_smix", "Yeh ΔS", ["HEA", "MEA", "dilute"]],
    ["tsai_sigma", "Tsai σ", ["sigma_unlikely", "sigma_prone", "not_applicable"]],
    ["sheikh_ductility", "Sheikh ductility", ["ductile", "borderline", "brittle"]],
  ];
  var designGate = new Gate($("design-gate"), {
    what: "Composition search and experiment planning.",
    needsCorpus: true,
    onReady: function () {},
  }).bind();
  var lastSearch = null;
  onShow("design", function () {
    if (autostart() && engine.available()) designGate.ensure().catch(function () {});
  });

  function propertyOptions(selected) {
    return PROPERTIES.map(function (p) {
      return '<option value="' + p[0] + '"' + (p[0] === selected ? " selected" : "") + ">" + esc(p[1]) + "</option>";
    }).join("");
  }

  function addObjective(direction, prop) {
    var row = document.createElement("div");
    row.className = "feature-repeat__row";
    row.innerHTML =
      '<select data-k="direction"><option value="maximize"' + (direction === "maximize" ? " selected" : "") + '>maximize</option><option value="minimize"' +
      (direction === "minimize" ? " selected" : "") + ">minimize</option></select><select data-k=\"prop\">" + propertyOptions(prop) +
      '</select><button type="button" class="ghost" data-remove>Remove</button>';
    $("search-objectives").appendChild(row);
  }

  function addLimit(prop) {
    var row = document.createElement("div");
    row.className = "feature-repeat__row";
    row.innerHTML =
      '<select data-k="prop">' + propertyOptions(prop) + '</select><input type="number" step="any" data-k="min" placeholder="min">' +
      '<input type="number" step="any" data-k="max" placeholder="max"><select data-k="bound"><option value="point">point estimate</option>' +
      '<option value="lower">interval lower end</option><option value="upper">interval upper end</option></select>' +
      '<button type="button" class="ghost" data-remove>Remove</button>';
    $("search-property-limits").appendChild(row);
  }

  function addElementLimit() {
    var row = document.createElement("div");
    row.className = "feature-repeat__row";
    row.innerHTML =
      '<input type="text" data-k="element" placeholder="element, e.g. Al" style="width:130px">' +
      '<input type="number" step="any" min="0" max="1" data-k="min" placeholder="min fraction">' +
      '<input type="number" step="any" min="0" max="1" data-k="max" placeholder="max fraction">' +
      '<button type="button" class="ghost" data-remove>Remove</button>';
    $("search-element-limits").appendChild(row);
  }

  $("search-rules").innerHTML = RULES.map(function (rule) {
    return (
      "<label>" + esc(rule[1]) + ' <select data-rule="' + rule[0] + '"><option value="">no requirement</option>' +
      rule[2].map(function (v) { return '<option value="' + v + '">' + esc(v.replace(/_/g, " ")) + "</option>"; }).join("") +
      "</select></label>"
    );
  }).join("");
  addObjective("maximize", "hardness");
  addObjective("minimize", "density");
  $("search-add-objective").addEventListener("click", function () {
    addObjective("minimize", "cost_per_kg");
  });
  $("search-add-limit").addEventListener("click", function () {
    addLimit("density");
  });
  $("search-add-element-limit").addEventListener("click", addElementLimit);
  $("search-form").addEventListener("click", function (event) {
    var remove = event.target.closest("[data-remove]");
    if (remove) remove.parentElement.remove();
  });

  function rowsOf(containerId) {
    return Array.prototype.map.call($(containerId).children, function (row) {
      var out = {};
      row.querySelectorAll("[data-k]").forEach(function (input) {
        out[input.getAttribute("data-k")] = input.value.trim();
      });
      return out;
    });
  }

  function searchParams() {
    var form = $("search-form");
    var params = {
      elements: elementsList(form.elements.palette.value),
      n_elements_min: parseInt(form.elements.n_elements_min.value, 10),
      n_elements_max: parseInt(form.elements.n_elements_max.value, 10),
      step: parseFloat(form.elements.step.value),
      objectives: rowsOf("search-objectives").map(function (r) {
        return [r.direction, r.prop];
      }),
      property_constraints: rowsOf("search-property-limits")
        .filter(function (r) {
          return r.min !== "" || r.max !== "";
        })
        .map(function (r) {
          return { prop: r.prop, min: r.min === "" ? null : parseFloat(r.min), max: r.max === "" ? null : parseFloat(r.max), bound: r.bound };
        }),
      composition_constraints: rowsOf("search-element-limits")
        .filter(function (r) {
          return r.element;
        })
        .map(function (r) {
          return { element: elementsList(r.element)[0], min: r.min === "" ? 0 : parseFloat(r.min), max: r.max === "" ? 1 : parseFloat(r.max) };
        }),
      rule_constraints: Array.prototype.filter
        .call($("search-rules").querySelectorAll("select"), function (s) {
          return s.value;
        })
        .map(function (s) {
          return { rule: s.getAttribute("data-rule"), satisfied: s.value };
        }),
      include_out_of_domain: form.elements.include_out_of_domain.checked,
      optimize_bound: form.elements.conservative.checked ? "lower" : "point",
      max_candidates: parseInt(form.elements.max_candidates.value, 10),
      alpha: parseFloat(form.elements.alpha.value),
    };
    if (!params.objectives.length) throw new Error("Add at least one objective.");
    return params;
  }

  function paretoPlot(result) {
    var objectives = result.settings.objectives;
    if (objectives.length < 2 || !result.candidates.length) return "";
    var xName = objectives[0][1];
    var yName = objectives[1][1];
    var pts = result.candidates.map(function (c) {
      return [c.objective_values[xName], c.objective_values[yName]];
    }).filter(function (p) {
      return isFinite(p[0]) && isFinite(p[1]);
    });
    if (!pts.length) return "";
    var xs = pts.map(function (p) { return p[0]; });
    var ys = pts.map(function (p) { return p[1]; });
    var pad = function (lo, hi) {
      var span = hi - lo || Math.abs(hi) || 1;
      return [lo - 0.08 * span, hi + 0.08 * span];
    };
    var xr = pad(Math.min.apply(null, xs), Math.max.apply(null, xs));
    var yr = pad(Math.min.apply(null, ys), Math.max.apply(null, ys));
    var W = 640, H = 340, L = 64, B = 44, T = 14, R = 14;
    var sx = function (v) { return L + ((v - xr[0]) / (xr[1] - xr[0])) * (W - L - R); };
    var sy = function (v) { return H - B - ((v - yr[0]) / (yr[1] - yr[0])) * (H - B - T); };
    var ticks = function (r) {
      var out = [];
      for (var i = 0; i <= 4; i++) out.push(r[0] + ((r[1] - r[0]) * i) / 4);
      return out;
    };
    var fmtTick = function (v) {
      return Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2);
    };
    var sorted = pts.slice().sort(function (a, b) { return a[0] - b[0]; });
    var label = function (name) {
      var p = PROPERTIES.filter(function (q) { return q[0] === name; })[0];
      var cautious =
        result.settings.optimize_bound === "lower" &&
        result.candidates.some(function (c) {
          return c.properties[name] && c.properties[name].interval;
        });
      return (p ? p[1] : name) + (cautious ? ", cautious interval end" : "");
    };
    return (
      '<div class="feature-plot"><svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Pareto front">' +
      '<line class="axis" x1="' + L + '" y1="' + (H - B) + '" x2="' + (W - R) + '" y2="' + (H - B) + '"/>' +
      '<line class="axis" x1="' + L + '" y1="' + T + '" x2="' + L + '" y2="' + (H - B) + '"/>' +
      ticks(xr).map(function (v) { return '<g class="tick"><text x="' + sx(v) + '" y="' + (H - B + 16) + '" text-anchor="middle">' + fmtTick(v) + "</text></g>"; }).join("") +
      ticks(yr).map(function (v) { return '<g class="tick"><text x="' + (L - 8) + '" y="' + (sy(v) + 4) + '" text-anchor="end">' + fmtTick(v) + "</text></g>"; }).join("") +
      '<polyline class="front-line" points="' + sorted.map(function (p) { return sx(p[0]) + "," + sy(p[1]); }).join(" ") + '"/>' +
      pts.map(function (p) { return '<circle class="pt-front" r="4" cx="' + sx(p[0]) + '" cy="' + sy(p[1]) + '"/>'; }).join("") +
      '<text class="label" x="' + ((W + L) / 2) + '" y="' + (H - 8) + '" text-anchor="middle">' + esc(objectives[0][0] + " " + label(xName)) + "</text>" +
      '<text class="label" transform="translate(14 ' + ((H - B) / 2) + ') rotate(-90)" text-anchor="middle">' + esc(objectives[1][0] + " " + label(yName)) + "</text>" +
      "</svg></div>"
    );
  }

  function renderSearch(result) {
    var objectives = result.settings.objectives;
    var head =
      "<tr><th>Composition</th>" +
      objectives.map(function (o) { return '<th class="num">' + esc(o[1].replace(/_/g, " ")) + "</th>"; }).join("") +
      "<th>Like the dataset</th><th>Rules</th><th></th></tr>";
    var body = result.candidates
      .map(function (c, i) {
        var cells = objectives
          .map(function (o) {
            var p = c.properties[o[1]];
            var interval = p && p.interval ? ' <span class="feature-note">[' + num(Math.max(0, p.interval[0]), 0) + ", " + num(p.interval[1], 0) + "]</span>" : "";
            var digits = p && p.value >= 100 ? 0 : 3;
            return '<td class="num">' + (p ? num(p.value, digits) : "n/a") + interval + "</td>";
          })
          .join("");
        var verdicts = Object.keys(c.rules)
          .map(function (k) { return k + ": " + c.rules[k]; })
          .join("\n");
        return (
          '<tr><td class="comp">' + compHtml(c.composition) + "</td>" + cells + "<td>" + (c.in_domain === null ? "n/a" : c.in_domain ? "yes" : "no") +
          '</td><td><span class="feature-badge" title="' + esc(verdicts) + '">' + Object.keys(c.rules).length + " verdicts</span>" +
          '</td><td><button type="button" class="ghost" data-open="' + i + '">Calculator</button></td></tr>'
        );
      })
      .join("");
    $("search-results").innerHTML =
      stats([
        [int(result.n_evaluated), "compositions screened"],
        [int(result.n_feasible), "meet every requirement"],
        [int(result.n_front), "on the Pareto front"],
        [int(result.candidates.length), "shown"],
      ]) +
      paretoPlot(result) +
      (result.candidates.length
        ? '<div class="table-wrap"><table class="data feature-table"><caption>Pareto-front alloys. Fitted properties show their interval; ranking ' +
          (result.settings.optimize_bound === "lower" ? "uses the cautious interval end" : "uses the point estimate") + ".</caption><thead>" + head + "</thead><tbody>" + body + "</tbody></table></div>"
        : '<p class="feature-note">No composition meets every requirement. Loosen a limit, widen the palette, or allow alloys unlike the dataset.</p>') +
      '<div class="feature-controls"><button type="button" class="ghost" id="search-download">Download the full result (JSON)</button></div>' +
      '<p class="feature-note">Hover a rule badge for all nine verdicts. Each candidate in the JSON carries its descriptors, rule verdicts, property predictions with intervals and its novelty measures.</p>';
  }

  $("search-form").addEventListener("submit", function (event) {
    event.preventDefault();
    var params;
    try {
      params = searchParams();
    } catch (error) {
      $("search-results").innerHTML = errorHtml(error);
      return;
    }
    designGate
      .ensure()
      .then(function () {
        return designGate.run("Searching", function (progress) {
          return engine.call("search", params, progress);
        });
      })
      .then(function (result) {
        lastSearch = result;
        renderSearch(result);
      })
      .catch(function (error) {
        $("search-results").innerHTML = errorHtml(error);
      });
  });
  $("search-results").addEventListener("click", function (event) {
    var open = event.target.closest("[data-open]");
    if (open && lastSearch) openInCalculator(lastSearch.candidates[Number(open.getAttribute("data-open"))].composition);
    if (event.target.id === "search-download" && lastSearch) download("hea-bench-search.json", JSON.stringify(lastSearch, null, 2), "application/json");
  });

  // ---------------------------------------------------------- design: campaign

  var lastSuggestions = null;

  function addObservation(obs) {
    var tr = document.createElement("tr");
    tr.innerHTML =
      '<td><input type="text" data-k="composition" placeholder="e.g. Al0.5CoCrFeNi" value="' + esc(obs ? obs.composition : "") + '"></td>' +
      '<td><input type="number" step="any" data-k="value" value="' + esc(obs && obs.value !== undefined ? obs.value : "") + '"></td>' +
      '<td><input type="text" data-k="processing" placeholder="e.g. CAST" value="' + esc(obs && obs.processing ? obs.processing : "") + '"></td>' +
      '<td><button type="button" class="ghost" data-remove>Remove</button></td>';
    $("campaign-obs-tbody").appendChild(tr);
    return tr;
  }

  function campaignPayload() {
    var form = $("campaign-form");
    var observations = [];
    Array.prototype.forEach.call($("campaign-obs-tbody").children, function (tr, index) {
      var get = function (k) {
        return tr.querySelector('[data-k="' + k + '"]').value.trim();
      };
      if (!get("composition") && !get("value")) return;
      if (!get("composition")) throw new Error("Measurement " + (index + 1) + " has no composition.");
      var value = parseFloat(get("value"));
      if (!isFinite(value)) throw new Error("Measurement " + (index + 1) + " has no measured value.");
      observations.push({ composition: get("composition"), value: value, processing: get("processing") || null, uncertainty: null });
    });
    return {
      schema: 1,
      hea_bench_version: (engine.status().info || {}).hea_bench_version,
      objective: form.elements.objective.value.trim() || "hardness",
      direction: form.elements.direction.value,
      palette: elementsList(form.elements.palette.value),
      constraints: [{ type: "DomainConstraint", in_domain: form.elements.in_domain.checked ? true : null }],
      seed: 0,
      step: parseFloat(form.elements.step.value),
      n_elements: [parseInt(form.elements.n_min.value, 10), parseInt(form.elements.n_max.value, 10)],
      warm_start: form.elements.warm_start.checked,
      observations: observations,
    };
  }

  function loadCampaign(payload) {
    var form = $("campaign-form");
    if (payload.schema !== 1) throw new Error("This campaign file uses schema " + payload.schema + "; this version reads schema 1.");
    form.elements.objective.value = payload.objective;
    form.elements.direction.value = payload.direction;
    form.elements.palette.value = (payload.palette || []).join(" ");
    var step = String(payload.step);
    if (!Array.prototype.some.call(form.elements.step.options, function (o) { return o.value === step; })) {
      form.elements.step.add(new Option(step, step));
    }
    form.elements.step.value = step;
    form.elements.n_min.value = payload.n_elements[0];
    form.elements.n_max.value = payload.n_elements[1];
    form.elements.warm_start.checked = !!payload.warm_start;
    var domain = (payload.constraints || []).filter(function (c) { return c.type === "DomainConstraint"; })[0];
    form.elements.in_domain.checked = !domain || domain.in_domain !== null;
    $("campaign-obs-tbody").innerHTML = "";
    (payload.observations || []).forEach(function (obs) {
      addObservation({
        composition: typeof obs.composition === "string" ? obs.composition : compText(obs.composition),
        value: obs.value,
        processing: obs.processing,
      });
    });
    if (!payload.observations || !payload.observations.length) addObservation(null);
  }

  addObservation(null);
  $("campaign-add-row").addEventListener("click", function () {
    addObservation(null).querySelector("input").focus();
  });
  $("campaign-obs-tbody").addEventListener("click", function (event) {
    var remove = event.target.closest("[data-remove]");
    if (remove) remove.closest("tr").remove();
  });
  $("campaign-save").addEventListener("click", function () {
    try {
      download("hea-bench-campaign.json", JSON.stringify(campaignPayload(), null, 2) + "\n", "application/json");
    } catch (error) {
      $("campaign-results").innerHTML = errorHtml(error);
    }
  });
  $("campaign-open").addEventListener("click", function () {
    $("campaign-file").click();
  });
  $("campaign-file").addEventListener("change", function () {
    readFile(this)
      .then(function (text) {
        loadCampaign(JSON.parse(text));
        $("campaign-results").innerHTML = '<p class="feature-note">Campaign loaded.</p>';
      })
      .catch(function (error) {
        $("campaign-results").innerHTML = errorHtml(error);
      });
  });
  $("campaign-suggest").addEventListener("click", function () {
    var payload;
    try {
      payload = campaignPayload();
    } catch (error) {
      $("campaign-results").innerHTML = errorHtml(error);
      return;
    }
    var n = Math.max(1, Math.min(10, parseInt($("campaign-n").value, 10) || 5));
    designGate
      .ensure()
      .then(function () {
        return designGate.run("Ranking untried compositions", function (progress) {
          return engine.call("campaign_suggest", { campaign: payload, n: n, strategy: $("campaign-strategy").value }, progress);
        });
      })
      .then(function (r) {
        lastSuggestions = r;
        var rows = r.suggestions
          .map(function (s, i) {
            return (
              '<tr><td class="comp">' + compHtml(s.composition) + '</td><td class="num">' + num(s.mean, s.mean >= 100 ? 0 : 3) + '</td><td class="num">' +
              num(s.interval[0], s.interval[0] >= 100 ? 0 : 3) + " to " + num(s.interval[1], s.interval[1] >= 100 ? 0 : 3) + "</td><td>" +
              (s.in_domain === null ? "n/a" : s.in_domain ? "yes" : "no") + '</td><td class="num">' + num(s.acquisition, 3) +
              '</td><td><button type="button" class="ghost" data-record="' + i + '">Record result</button> <button type="button" class="ghost" data-open="' + i + '">Calculator</button></td></tr>'
            );
          })
          .join("");
        $("campaign-results").innerHTML =
          '<div class="table-wrap"><table class="data feature-table"><caption>Next ' + r.suggestions.length + " alloys to make for " + esc(r.direction) + " " + esc(r.objective) +
          ", from " + int(r.n_informative) + " informative rows (" + int(r.n_observations) + " of them yours), ranked by " +
          (r.strategy === "ei" ? "expected improvement" : "upper confidence bound") + ".</caption>" +
          '<thead><tr><th>Composition</th><th class="num">Predicted</th><th class="num">Model spread</th><th>Like your data</th><th class="num">Score</th><th></th></tr></thead><tbody>' +
          rows + "</tbody></table></div>" +
          '<p class="feature-note">The spread is the 2.5 to 97.5 percentile of the forest\'s trees, a measure of model disagreement rather than a calibrated interval. Make an alloy, then use Record result to add your measurement and ask again.</p>';
      })
      .catch(function (error) {
        $("campaign-results").innerHTML = errorHtml(error);
      });
  });
  $("campaign-results").addEventListener("click", function (event) {
    if (!lastSuggestions) return;
    var record = event.target.closest("[data-record]");
    var open = event.target.closest("[data-open]");
    if (record) {
      var s = lastSuggestions.suggestions[Number(record.getAttribute("data-record"))];
      var tbody = $("campaign-obs-tbody");
      var blank = Array.prototype.filter.call(tbody.children, function (tr) {
        return !tr.querySelector('[data-k="composition"]').value && !tr.querySelector('[data-k="value"]').value;
      })[0];
      var tr = blank || addObservation(null);
      tr.querySelector('[data-k="composition"]').value = compText(s.composition);
      tr.querySelector('[data-k="value"]').focus();
    }
    if (open) openInCalculator(lastSuggestions.suggestions[Number(open.getAttribute("data-open"))].composition);
  });

  window.HEAFeatures = { openInCalculator: openInCalculator, ceramicCalculate: ceramicCalculate };
})();
