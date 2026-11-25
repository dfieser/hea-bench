// The Calculator tab's page code: the composition form and results, the
// maps, saved results, custom elements and the pair-enthalpy editor, the
// oxide mode, the provenance drawer, receipts and citations, the element
// data view and the theme. Every number comes from hea-calculator-core.js
// (calcCore) or the engine. It runs as a classic script right after the
// inline block in index.html that holds VERSION, VERSION_HISTORY,
// ELEMENT_DATA and the generated provenance tables, which the release
// tools and tests/data/_sync_js_provenance.py rewrite in place.
      // The Miedema SS/amorphous/compound decomposition lives in the
      // parity-tested core; calcCore.MIEDEMA_TABLE is generated from the
      // vendored matminer Miedema.csv by tests/data/_sync_js_tables.py.
      // The page passes its live element table so custom elements keep
      // their melting/valence terms.
      function calculateMiedemaDescriptors(elements, fractions) {
        return calcCore.calculateMiedemaDescriptors(elements, fractions, {
          elementData: ELEMENT_DATA,
        });
      }

      const ratioTableEl = document.getElementById("ratio-table");
      const calculateBtn = document.getElementById("calculate");
      const errorEl = document.getElementById("error");
      const resultsEl = document.getElementById("results");
      const miedemaResultsEl = document.getElementById("miedema-results");
      const miedemaPanelEl = document.getElementById("miedema-panel");
      const warningsEl = document.getElementById("warnings");
      const pairEnthalpyEditorEl = document.getElementById("pair-enthalpy-editor");
      const saveResultBtn = document.getElementById("save-result");
      const downloadCsvBtn = document.getElementById("download-csv");
      const savedResultsBodyEl = document.getElementById("saved-results-body");
      const saveMessageEl = document.getElementById("save-message");
      const loadExampleBtn = document.getElementById("load-example");
      const normalizeBtn = document.getElementById("normalize");
      const equimolarBtn = document.getElementById("equimolar");
      const resetBtn = document.getElementById("reset");
      const elementCountInput = document.getElementById("element-count");
      const formulaInput = document.getElementById("formula-input");
      const kingTemperatureInput = document.getElementById("king-temperature");
      const parseFormulaBtn = document.getElementById("parse-formula");
      const shareUrlBtn = document.getElementById("share-url");

      const customPanelEl = document.getElementById("custom-element-panel");
      const customLabelInput = document.getElementById("custom-label");
      const customRadiusInput = document.getElementById("custom-radius");
      const customMeltingInput = document.getElementById("custom-melting");
      const customValenceInput = document.getElementById("custom-valence");
      const customChiInput = document.getElementById("custom-chi");
      const customSaveBtn = document.getElementById("custom-save");
      const customCancelBtn = document.getElementById("custom-cancel");
      const customRemoveBtn = document.getElementById("custom-remove");
      const customMessageEl = document.getElementById("custom-message");

      const customElementsSectionEl = document.getElementById("custom-elements-section");
      const customElementsBodyEl = document.getElementById("custom-elements-body");

      let pairEnthalpyEdits = {};
      let savedResults = [];
      let lastCalculation = null;

      let customElements = [];
      let customEditOriginalLabel = null;
      let customTriggeredSelectIndex = null;

      function safeJsonParse(raw) {
        try {
          return JSON.parse(raw);
        } catch {
          return null;
        }
      }

      let formSaveTimer = null;

      function clearSavedFormState() {
        localStorage.removeItem(STORAGE_KEYS.formState);
      }

      function clearSavedResultsState() {
        localStorage.removeItem(STORAGE_KEYS.savedResults);
      }

      function sanitizeSavedResults(candidate) {
        if (!Array.isArray(candidate)) return [];
        const cleaned = [];
        for (const item of candidate) {
          if (!item || typeof item !== "object") continue;
          const id = String(item.id || "");
          const timestamp = Number(item.timestamp);
          const elements = Array.isArray(item.elements) ? item.elements.map((v) => String(v || "")).filter(Boolean) : [];
          const percents = item.percents && typeof item.percents === "object" ? item.percents : null;
          const descriptors = item.descriptors && typeof item.descriptors === "object" ? item.descriptors : null;

          if (!id) continue;
          if (!Number.isFinite(timestamp)) continue;
          if (elements.length < 2) continue;
          if (!percents || !descriptors) continue;

          const percentsClean = {};
          let okPercents = true;
          elements.forEach((el) => {
            const v = Number(percents[el]);
            if (!Number.isFinite(v)) okPercents = false;
            percentsClean[el] = v;
          });
          if (!okPercents) continue;

          const d = {
            Smix: Number(descriptors.Smix),
            delta: Number(descriptors.delta),
            Tm_K: Number(descriptors.Tm_K),
            Tm_C: Number(descriptors.Tm_C),
            Hmix: Number(descriptors.Hmix),
            VEC: Number(descriptors.VEC),
            Omega: Number(descriptors.Omega),
            delta_chi: descriptors.delta_chi != null ? Number(descriptors.delta_chi) : null,
            mean_chi: descriptors.mean_chi != null ? Number(descriptors.mean_chi) : null,
            S_excess: descriptors.S_excess != null ? Number(descriptors.S_excess) : null,
            DeltaG_ss: descriptors.DeltaG_ss != null ? Number(descriptors.DeltaG_ss) : null,
            DeltaG_max: descriptors.DeltaG_max != null ? Number(descriptors.DeltaG_max) : null,
            Phi_king: descriptors.Phi_king != null ? Number(descriptors.Phi_king) : null,
            Phi_ye: descriptors.Phi_ye != null ? Number(descriptors.Phi_ye) : null,
            King_temperature_K: descriptors.King_temperature_K != null ? Number(descriptors.King_temperature_K) : null,
            H_compound: descriptors.H_compound != null ? Number(descriptors.H_compound) : null,
            H_SS_total: descriptors.H_SS_total != null ? Number(descriptors.H_SS_total) : null,
            H_SS_chem: descriptors.H_SS_chem != null ? Number(descriptors.H_SS_chem) : null,
            H_SS_elast: descriptors.H_SS_elast != null ? Number(descriptors.H_SS_elast) : null,
            H_SS_struct: descriptors.H_SS_struct != null ? Number(descriptors.H_SS_struct) : null,
            H_AM_total: descriptors.H_AM_total != null ? Number(descriptors.H_AM_total) : null,
            H_AM_chem: descriptors.H_AM_chem != null ? Number(descriptors.H_AM_chem) : null,
            H_AM_topo: descriptors.H_AM_topo != null ? Number(descriptors.H_AM_topo) : null,
          };

          cleaned.push({
            id,
            timestamp,
            elements,
            percents: percentsClean,
            descriptors: d,
          });
        }

        // Keep newest first; cap size to avoid unbounded growth.
        cleaned.sort((a, b) => Number(b.timestamp) - Number(a.timestamp));
        return cleaned.slice(0, 250);
      }

      function saveSavedResultsNow() {
        try {
          localStorage.setItem(STORAGE_KEYS.savedResults, JSON.stringify(savedResults));
        } catch {
          // Ignore storage quota/availability issues.
        }
      }

      function loadSavedResults() {
        const parsed = safeJsonParse(localStorage.getItem(STORAGE_KEYS.savedResults));
        return sanitizeSavedResults(parsed);
      }

      function sanitizePairEdits(candidate) {
        if (!candidate || typeof candidate !== "object") return {};
        const cleaned = {};
        Object.entries(candidate).forEach(([key, value]) => {
          const k = String(key || "");
          if (!/^[A-Za-z0-9_\-]{1,10}\|[A-Za-z0-9_\-]{1,10}$/.test(k)) return;
          const num = Number(value);
          if (!Number.isFinite(num)) return;
          cleaned[k] = num;
        });
        return cleaned;
      }

      function snapshotFormState() {
        const count = Math.min(10, Math.max(2, Number(elementCountInput.value) || 5));
        const { elements, percents } = readComposition();

        const cleanedElements = (elements || []).map((el) => {
          if (!el) return "";
          if (el === CUSTOM_OPTION_VALUE) return "";
          if (!ELEMENT_DATA[el]) return "";
          return el;
        });

        const cleanedPercents = (percents || []).map((p) => {
          const num = Number(p);
          return Number.isFinite(num) ? num : null;
        });

        return {
          elementCount: count,
          elements: cleanedElements,
          percents: cleanedPercents,
          kingTemperature: (() => {
            const value = Number(kingTemperatureInput.value);
            return Number.isFinite(value) && value > 0 ? value : null;
          })(),
          pairEnthalpyEdits: { ...pairEnthalpyEdits },
          savedAt: Date.now(),
        };
      }

      function saveFormStateNow() {
        try {
          localStorage.setItem(STORAGE_KEYS.formState, JSON.stringify(snapshotFormState()));
        } catch {
          // Ignore storage quota/availability issues.
        }
      }

      function scheduleSaveFormState() {
        if (formSaveTimer) window.clearTimeout(formSaveTimer);
        formSaveTimer = window.setTimeout(() => {
          formSaveTimer = null;
          saveFormStateNow();
        }, 250);
      }

      function loadFormState() {
        const parsed = safeJsonParse(localStorage.getItem(STORAGE_KEYS.formState));
        if (!parsed || typeof parsed !== "object") return null;

        const elementCount = Math.min(10, Math.max(2, Number(parsed.elementCount) || 5));
        const elements = Array.isArray(parsed.elements)
          ? parsed.elements.map((v) => String(v || ""))
          : [];
        const percents = Array.isArray(parsed.percents)
          ? parsed.percents.map((v) => Number(v))
          : [];

        return {
          elementCount,
          elements,
          percents,
          kingTemperature: parsed.kingTemperature != null ? Number(parsed.kingTemperature) : null,
          pairEnthalpyEdits: sanitizePairEdits(parsed.pairEnthalpyEdits),
        };
      }

      function applyFormState(state) {
        if (!state) return false;
        const count = Math.min(10, Math.max(2, Number(state.elementCount) || 5));
        elementCountInput.value = count;
        renderRatioTable(count);

        ratioTableEl.querySelectorAll("select[data-element-index]").forEach((select, idx) => {
          const value = state.elements?.[idx] || "";
          if (value && value !== CUSTOM_OPTION_VALUE && ELEMENT_DATA[value]) {
            if (Array.from(select.options).some((opt) => opt.value === value)) {
              select.value = value;
              return;
            }
          }
          select.value = "";
        });

        ratioTableEl.querySelectorAll("input[data-percent-index]").forEach((input, idx) => {
          const value = Number(state.percents?.[idx]);
          if (Number.isFinite(value)) setPercent(input, value);
        });

        if (state.kingTemperature != null && Number.isFinite(state.kingTemperature) && state.kingTemperature > 0) {
          kingTemperatureInput.value = String(state.kingTemperature);
        } else {
          kingTemperatureInput.value = "";
        }

        pairEnthalpyEdits = state.pairEnthalpyEdits ? { ...state.pairEnthalpyEdits } : {};
        renderPairEnthalpyEditor();
        return true;
      }

      function getAvailableElements() {
        return Object.keys(ELEMENT_DATA).sort();
      }

      function isValidCustomLabel(label) {
        if (!label) return false;
        if (label === CUSTOM_OPTION_VALUE) return false;
        if (!/^[A-Za-z0-9][A-Za-z0-9_\-]{0,9}$/.test(label)) return false;
        if (BUILTIN_ELEMENT_LABELS.has(label)) return false;
        return true;
      }

      function normaliseCustomElementRecord(record) {
        if (!record || typeof record !== "object") return null;
        const label = String(record.label || "").trim();
        const radius = Number(record.radius);
        const melting = Number(record.melting);
        const valence = Number(record.valence);
        if (!isValidCustomLabel(label)) return null;
        if (!Number.isFinite(radius) || radius <= 0) return null;
        if (!Number.isFinite(melting) || melting <= 0) return null;
        if (!Number.isFinite(valence) || valence < 0) return null;
        return { label, radius, melting, valence };
      }

      function loadCustomElements() {
        const raw = localStorage.getItem(STORAGE_KEYS.customElements);
        const parsed = safeJsonParse(raw);
        if (!Array.isArray(parsed)) return [];
        const cleaned = [];
        const seen = new Set();
        parsed.forEach((item) => {
          const normal = normaliseCustomElementRecord(item);
          if (!normal) return;
          if (seen.has(normal.label)) return;
          seen.add(normal.label);
          cleaned.push(normal);
        });
        cleaned.sort((a, b) => a.label.localeCompare(b.label));
        return cleaned;
      }

      function saveCustomElements(list) {
        localStorage.setItem(STORAGE_KEYS.customElements, JSON.stringify(list));
      }

      function applyCustomElementsToData(list) {
        (list || []).forEach((item) => {
          ELEMENT_DATA[item.label] = {
            radius: item.radius,
            melting: item.melting,
            valence: item.valence,
            chi: Number.isFinite(item.chi) ? item.chi : NaN,
          };
        });
      }

      function removeCustomFromData(label) {
        if (!label) return;
        if (BUILTIN_ELEMENT_LABELS.has(label)) return;
        if (ELEMENT_DATA[label]) delete ELEMENT_DATA[label];
      }

      function renderCustomElementsSection() {
        customElementsBodyEl.innerHTML = "";
        if (!customElements.length) {
          customElementsSectionEl.classList.add("hidden");
          return;
        }
        customElementsSectionEl.classList.remove("hidden");

        customElements.forEach((item) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${item.label}</td>
            <td>${formatNumber(item.radius)}</td>
            <td>${formatNumber(item.melting)}</td>
            <td>${formatNumber(item.valence)}</td>
            <td>
              <button class="ghost" data-custom-edit="${item.label}">Edit</button>
              <button class="ghost" data-custom-delete="${item.label}">Delete</button>
            </td>
          `;
          customElementsBodyEl.appendChild(tr);
        });
      }

      function showCustomMessage(message) {
        customMessageEl.textContent = message || "";
      }

      function openCustomPanel(selectIndex, editLabel = null) {
        customTriggeredSelectIndex = Number.isFinite(selectIndex) ? selectIndex : null;
        customEditOriginalLabel = editLabel;
        showCustomMessage("");
        const current = editLabel ? customElements.find((e) => e.label === editLabel) : null;
        if (current) {
          customLabelInput.value = current.label;
          customRadiusInput.value = current.radius;
          customMeltingInput.value = current.melting;
          customValenceInput.value = current.valence;
          customChiInput.value = Number.isFinite(current.chi) ? current.chi : "";
          customRemoveBtn.disabled = false;
        } else {
          customLabelInput.value = "";
          customRadiusInput.value = "";
          customMeltingInput.value = "";
          customValenceInput.value = "";
          customChiInput.value = "";
          customRemoveBtn.disabled = true;
        }
        customPanelEl.classList.remove("hidden");
      }

      function closeCustomPanel() {
        customTriggeredSelectIndex = null;
        customEditOriginalLabel = null;
        showCustomMessage("");
        customPanelEl.classList.add("hidden");
      }

      function remapPairEnthalpyEdits(oldLabel, newLabel) {
        if (!oldLabel || !newLabel || oldLabel === newLabel) return;
        const next = {};
        Object.entries(pairEnthalpyEdits).forEach(([key, value]) => {
          const [a, b] = key.split("|");
          if (!a || !b) return;
          const aa = a === oldLabel ? newLabel : a;
          const bb = b === oldLabel ? newLabel : b;
          const newKey = getPairKey(aa, bb);
          next[newKey] = value;
        });
        pairEnthalpyEdits = next;
      }

      function deleteCustomElementByLabel(label) {
        if (!label) return;
        const exists = customElements.some((e) => e.label === label);
        if (!exists) return;

        customElements = customElements.filter((e) => e.label !== label);
        saveCustomElements(customElements);
        removeCustomFromData(label);

        const snapshot = snapshotCompositionTable();
        renderRatioTable(Number(elementCountInput.value) || 5);
        if (snapshot) {
          snapshot.elements = snapshot.elements.map((v) => (v === label ? "" : v));
          restoreCompositionTable(snapshot);
        }
        renderPairEnthalpyEditor();
        renderCustomElementsSection();
      }

      function snapshotCompositionTable() {
        const { elements, percents } = readComposition();
        return { elements: [...elements], percents: [...percents] };
      }

      function restoreCompositionTable(snapshot) {
        if (!snapshot) return;
        ratioTableEl.querySelectorAll("select[data-element-index]").forEach((select, idx) => {
          const value = snapshot.elements[idx] || "";
          if (Array.from(select.options).some((opt) => opt.value === value)) {
            select.value = value;
          } else {
            select.value = "";
          }
        });
        ratioTableEl.querySelectorAll("input[data-percent-index]").forEach((input, idx) => {
          const value = snapshot.percents[idx];
          if (Number.isFinite(value)) setPercent(input, value);
        });
      }

      function renderRatioTable(count) {
        const availableElements = getAvailableElements();
        const rows = Array.from({ length: count }).map((_, index) => {
          const options = [
            '<option value="">Select</option>',
            ...availableElements.map((el) => `<option value="${el}">${el}</option>`),
            `<option value="${CUSTOM_OPTION_VALUE}">Custom element…</option>`,
          ].join("");
          return `
            <tr>
              <td>
                <select data-element-index="${index}">${options}</select>
              </td>
              <td>
                <input type="number" min="0" step="0.1" data-percent-index="${index}" value="${(100 / count).toFixed(2)}" data-exact="${100 / count}" />
              </td>
            </tr>
          `;
        });

        ratioTableEl.innerHTML = `
          <table>
            <thead>
              <tr><th>Element</th><th>Percent (%)</th></tr>
            </thead>
            <tbody>${rows.join("")}</tbody>
          </table>
        `;
      }

      // A percent box shows 0.01 at.%, but a typed formula or a permalink
      // carries more. The exact amount rides in data-exact until the user
      // edits the box, so the app computes on what was typed, as the
      // library does.
      function setPercent(input, value) {
        input.value = value.toFixed(2);
        input.dataset.exact = String(value);
      }

      function readPercent(input) {
        const exact = Number(input.dataset.exact);
        return input.dataset.exact && exact.toFixed(2) === input.value ? exact : Number(input.value);
      }

      function readComposition() {
        const elements = [];
        const percents = [];
        ratioTableEl.querySelectorAll("select[data-element-index]").forEach((select) => {
          elements.push(select.value);
        });
        ratioTableEl.querySelectorAll("input[data-percent-index]").forEach((input) => {
          percents.push(readPercent(input));
        });
        return { elements, percents };
      }

      function formatNumber(value, digits = 4) {
        if (!Number.isFinite(value)) {
          return "∞";
        }
        return Number(value).toPrecision(digits);
      }

      function getKingTemperatureOverride() {
        const value = Number(kingTemperatureInput.value);
        if (Number.isFinite(value) && value > 0) {
          return value;
        }
        return null;
      }

      function formatVerdict(value) {
        if (!value) {
          return "—";
        }
        return String(value).replace(/_/g, " ");
      }

      function showError(message) {
        if (!message) {
          errorEl.classList.add("hidden");
          errorEl.textContent = "";
          return;
        }
        errorEl.textContent = message;
        errorEl.classList.remove("hidden");
      }

      function showSaveMessage(message) {
        saveMessageEl.textContent = message || "";
      }

      // ---- Phase-selection maps (inline SVG, no libraries) ----------
      // Regions are the published empirical windows; the current alloy
      // is plotted as one accent point (clamped to the frame with an
      // open marker and a caption note when off scale).

      function mapScale(domainMin, domainMax, rangeMin, rangeMax) {
        const k = (rangeMax - rangeMin) / (domainMax - domainMin);
        return (v) => rangeMin + (v - domainMin) * k;
      }

      function mapClamp(v, lo, hi) {
        return Math.min(hi, Math.max(lo, v));
      }

      function mapFmt(v, digits = 2) {
        if (v === null || v === undefined || !isFinite(v)) return "∞";
        return Number(v).toFixed(digits);
      }

      function refJumpLink(refKey, label) {
        return '<a href="#refs" data-jump-view="refs" data-jump-anchor="ref-' + refKey + '">' + label + "</a>";
      }

      function buildZhangMap(d) {
        const X = mapScale(0, 16, 46, 450);
        const Y = mapScale(20, -50, 10, 264); // +20 kJ/mol at top
        const px = mapClamp(d.delta, 0, 16);
        const py = mapClamp(d.Hmix, -50, 20);
        const off = px !== d.delta || py !== d.Hmix;
        const xTicks = [0, 4, 8, 12, 16];
        const yTicks = [20, 0, -20, -40];
        let s = '<svg viewBox="0 0 460 300" role="img" aria-label="Atomic size mismatch versus mixing enthalpy map with the published solid-solution and glass-forming regions and this alloy plotted">';
        yTicks.forEach((t) => {
          s += '<line class="map-grid-line" x1="46" x2="450" y1="' + Y(t) + '" y2="' + Y(t) + '"/>';
          s += '<text class="map-tick-label" x="40" y="' + (Y(t) + 3) + '" text-anchor="end">' + t + "</text>";
        });
        xTicks.forEach((t) => {
          s += '<text class="map-tick-label" x="' + X(t) + '" y="278" text-anchor="middle">' + t + "</text>";
        });
        // Guo-Liu 2011 SS envelope (dashed), Zhang 2008 SS window (tinted), Guo-Liu BMG region.
        s += '<rect class="map-region--ss2" x="' + X(0) + '" y="' + Y(7) + '" width="' + (X(8.5) - X(0)) + '" height="' + (Y(-22) - Y(7)) + '"/>';
        s += '<rect class="map-region--ss" x="' + X(1) + '" y="' + Y(5) + '" width="' + (X(6) - X(1)) + '" height="' + (Y(-15) - Y(5)) + '"/>';
        s += '<rect class="map-region--bmg" x="' + X(9) + '" y="' + Y(-5.5) + '" width="' + (X(16) - X(9)) + '" height="' + (Y(-49) - Y(-5.5)) + '"/>';
        s += '<text class="map-region-label" x="' + (X(1) + 6) + '" y="' + (Y(-15) - 6) + '">SS · Zhang 2008</text>';
        s += '<text class="map-region-label" x="' + (X(0) + 6) + '" y="' + (Y(7) + 14) + '">SS envelope · Guo-Liu 2011</text>';
        s += '<text class="map-region-label" x="' + (X(9) + 6) + '" y="' + (Y(-5.5) + 14) + '">BMG · Guo-Liu 2011</text>';
        s += '<line class="map-axis" x1="46" x2="46" y1="10" y2="264"/><line class="map-axis" x1="46" x2="450" y1="264" y2="264"/>';
        s += '<text class="map-axis-title" x="248" y="294" text-anchor="middle">δ (%)</text>';
        s += '<text class="map-axis-title" x="14" y="137" text-anchor="middle" transform="rotate(-90 14 137)">ΔH mix (kJ/mol)</text>';
        s += '<circle class="' + (off ? "map-point--offscale" : "map-point") + '" cx="' + X(px) + '" cy="' + Y(py) + '" r="5"><title>δ = ' + mapFmt(d.delta) + " %, ΔH mix = " + mapFmt(d.Hmix) + " kJ/mol</title></circle>";
        s += "</svg>";
        return { svg: s, off: off };
      }

      function buildOmegaDeltaMap(d) {
        const X = mapScale(0, 12, 46, 450);
        const tY = mapScale(2, -2, 10, 264); // log10(Omega): 100 at top
        const logOmega = d.Omega === null ? null : (isFinite(d.Omega) ? Math.log10(Math.max(d.Omega, 1e-6)) : Infinity);
        const px = mapClamp(d.delta, 0, 12);
        const pt = logOmega === null ? null : mapClamp(logOmega, -2, 2);
        const off = px !== d.delta || (logOmega !== null && pt !== logOmega);
        const yTicks = [{ v: 2, label: "100" }, { v: 1, label: "10" }, { v: 0, label: "1" }, { v: -1, label: "0.1" }, { v: -2, label: "0.01" }];
        const xTicks = [0, 3, 6, 9, 12];
        let s = '<svg viewBox="0 0 460 300" role="img" aria-label="Omega versus atomic size mismatch map with the Yang-Zhang solid-solution quadrant and this alloy plotted">';
        yTicks.forEach((t) => {
          s += '<line class="map-grid-line" x1="46" x2="450" y1="' + tY(t.v) + '" y2="' + tY(t.v) + '"/>';
          s += '<text class="map-tick-label" x="40" y="' + (tY(t.v) + 3) + '" text-anchor="end">' + t.label + "</text>";
        });
        xTicks.forEach((t) => {
          s += '<text class="map-tick-label" x="' + X(t) + '" y="278" text-anchor="middle">' + t + "</text>";
        });
        s += '<rect class="map-region--ss" x="' + X(0) + '" y="' + tY(2) + '" width="' + (X(6.6) - X(0)) + '" height="' + (tY(Math.log10(1.1)) - tY(2)) + '"/>';
        s += '<text class="map-region-label" x="' + (X(0) + 6) + '" y="' + (tY(2) + 14) + '">SS · Yang-Zhang 2012</text>';
        s += '<line class="map-threshold" x1="46" x2="450" y1="' + tY(Math.log10(1.1)) + '" y2="' + tY(Math.log10(1.1)) + '"/>';
        s += '<text class="map-note" x="446" y="' + (tY(Math.log10(1.1)) - 4) + '" text-anchor="end">Ω = 1.1</text>';
        s += '<line class="map-threshold" x1="' + X(6.6) + '" x2="' + X(6.6) + '" y1="10" y2="264"/>';
        s += '<text class="map-note" x="' + (X(6.6) + 4) + '" y="20">δ = 6.6</text>';
        s += '<line class="map-axis" x1="46" x2="46" y1="10" y2="264"/><line class="map-axis" x1="46" x2="450" y1="264" y2="264"/>';
        s += '<text class="map-axis-title" x="248" y="294" text-anchor="middle">δ (%)</text>';
        s += '<text class="map-axis-title" x="14" y="137" text-anchor="middle" transform="rotate(-90 14 137)">Ω (log scale)</text>';
        if (pt !== null) {
          s += '<circle class="' + (off ? "map-point--offscale" : "map-point") + '" cx="' + X(px) + '" cy="' + tY(pt) + '" r="5"><title>δ = ' + mapFmt(d.delta) + " %, Ω = " + mapFmt(d.Omega) + "</title></circle>";
        }
        return { svg: s + "</svg>", off: off || pt === null };
      }

      function buildVecStrip(d) {
        const X = mapScale(0, 12, 30, 910);
        const vec = d.VEC;
        const px = mapClamp(vec, 0, 12);
        const off = px !== vec;
        const sigmaActive = d.sigma_former_present === true;
        let s = '<svg viewBox="0 0 940 132" role="img" aria-label="Valence electron concentration bands with the sigma-phase window, the refractory ductility line, and this alloy marked">';
        // Structure bands (Guo 2011), 2px surface gaps at the boundaries.
        s += '<rect class="map-band" fill-opacity="0.10" x="' + X(0) + '" y="40" width="' + (X(6.87) - X(0) - 1) + '" height="30"/>';
        s += '<rect class="map-band" fill-opacity="0.18" x="' + (X(6.87) + 1) + '" y="40" width="' + (X(8) - X(6.87) - 2) + '" height="30"/>';
        s += '<rect class="map-band" fill-opacity="0.10" x="' + (X(8) + 1) + '" y="40" width="' + (X(12) - X(8) - 1) + '" height="30"/>';
        s += '<text class="map-region-label" x="' + (X(0) + 6) + '" y="58">BCC &lt; 6.87 · Guo 2011</text>';
        s += '<text class="map-region-label" x="' + (X(6.87) + 5) + '" y="34">duplex</text>';
        s += '<text class="map-region-label" x="' + (X(8) + 6) + '" y="58">FCC ≥ 8 · Guo 2011</text>';
        // Sigma window overlay (Tsai 2013), above the band so the axis
        // tick labels stay clear.
        s += '<g opacity="' + (sigmaActive ? "1" : "0.35") + '">';
        s += '<rect class="map-region--warn" x="' + X(6.88) + '" y="8" width="' + (X(7.84) - X(6.88)) + '" height="12"/>';
        s += '<text class="map-note" x="' + (X(7.84) + 8) + '" y="17">σ window 6.88-7.84 · Tsai 2013' + (sigmaActive ? "" : " (no Cr/V here)") + "</text>";
        s += "</g>";
        // Sheikh ductility line (refractory bcc alloys).
        s += '<line class="map-threshold" x1="' + X(4.5) + '" x2="' + X(4.5) + '" y1="24" y2="70"/>';
        s += '<text class="map-note" x="' + (X(4.5) - 6) + '" y="20" text-anchor="end">&lt; 4.5 ductile RHEA · Sheikh 2016</text>';
        // Axis + integer ticks.
        s += '<line class="map-axis" x1="30" x2="910" y1="70" y2="70"/>';
        for (let t = 0; t <= 12; t += 1) {
          s += '<line class="map-axis" x1="' + X(t) + '" x2="' + X(t) + '" y1="70" y2="74"/>';
          s += '<text class="map-tick-label" x="' + X(t) + '" y="86" text-anchor="middle">' + t + "</text>";
        }
        s += '<text class="map-axis-title" x="470" y="104" text-anchor="middle">VEC (electrons/atom)</text>';
        // Alloy marker.
        s += '<line x1="' + X(px) + '" x2="' + X(px) + '" y1="28" y2="70" stroke="var(--accent)" stroke-width="2"/>';
        s += '<path class="' + (off ? "map-point--offscale" : "map-point") + '" d="M ' + (X(px) - 6) + ' 22 L ' + (X(px) + 6) + " 22 L " + X(px) + ' 32 Z"><title>VEC = ' + mapFmt(vec) + "</title></path>";
        s += '<text class="map-point-label" x="' + mapClamp(X(px) + 10, 40, 830) + '" y="30">VEC ' + mapFmt(vec) + "</text>";
        return { svg: s + "</svg>", off: off };
      }

      function renderMaps(payload) {
        const panel = document.getElementById("maps-panel");
        const grid = document.getElementById("maps-grid");
        if (!panel || !grid) return;
        if (!payload || !payload.descriptors) {
          panel.classList.add("hidden");
          grid.innerHTML = "";
          return;
        }
        const d = payload.descriptors;
        if (!isFiniteNumber(d.delta)) {
          panel.classList.add("hidden");
          grid.innerHTML = "";
          return;
        }
        const zhang = d.Hmix === null ? null : buildZhangMap(d);
        const omegaMap = buildOmegaDeltaMap(d);
        const vecStrip = buildVecStrip(d);
        const offNote = ' <span class="small-note">Open marker: point clamped to the frame (off scale).</span>';
        let html = "";
        if (zhang) {
          html += '<figure class="map-figure"><div class="map-title">δ vs ΔH mix</div>' + zhang.svg +
            "<figcaption>Solid-solution windows from " + refJumpLink("zhang2008", "Zhang 2008") + " (δ 1-6 %, ΔH −15…+5 kJ/mol) and " +
            refJumpLink("guo2011pnsmi", "Guo &amp; Liu 2011") + " (δ ≤ 8.5 %, ΔH −22…+7 kJ/mol). The glass-forming region follows the same survey." + (zhang.off ? offNote : "") + "</figcaption></figure>";
        }
        html += '<figure class="map-figure"><div class="map-title">Ω vs δ</div>' + omegaMap.svg +
          "<figcaption>Single-phase quadrant Ω ≥ 1.1 and δ ≤ 6.6 % from " + refJumpLink("yang2012", "Yang &amp; Zhang 2012") + "." + (omegaMap.off ? offNote : "") + "</figcaption></figure>";
        html += '<figure class="map-figure map-figure--wide"><div class="map-title">VEC bands</div>' + vecStrip.svg +
          "<figcaption>Structure bands from " + refJumpLink("guo2011vec", "Guo et al. 2011") + ", the σ-phase window (annealed Cr/V alloys) from " +
          refJumpLink("tsai2013", "Tsai et al. 2013") + ", and the refractory ductility line from " + refJumpLink("sheikh2016", "Sheikh et al. 2016") + "." + (vecStrip.off ? offNote : "") + "</figcaption></figure>";
        grid.innerHTML = html;
        panel.classList.remove("hidden");
      }

      function isFiniteNumber(v) {
        return typeof v === "number" && isFinite(v);
      }

      function renderResults(payload) {
        document.dispatchEvent(new CustomEvent("hea:alloy-result", { detail: payload || null }));
        resultsEl.innerHTML = "";
        miedemaResultsEl.innerHTML = "";
        const rulesPanelEl = document.getElementById("rules-panel");
        const rulesEl = document.getElementById("rule-predictions");
        rulesEl.innerHTML = "";
        if (!payload) {
          miedemaPanelEl.classList.add("hidden");
          rulesPanelEl.classList.add("hidden");
          renderMaps(null);
          renderCitePanel(null);
          return;
        }
        renderMaps(payload);
        provRememberAlloy(payload);
        renderCitePanel("alloy");

        const { composition, descriptors } = payload;
        const rules = payload.rules || calcCore.rulePredictionsFromDescriptors(descriptors, {
          kingThreshold: calcCore.KING_PHI_THRESHOLD,
          yeThreshold: calcCore.YE_PHI_THRESHOLD,
        });
        const compositionItems = Object.entries(composition)
          .map(
            ([k, v]) =>
              `<div class="composition-cell"><div class="element">${k}</div><div class="fraction">${formatNumber(v, 4)}</div></div>`
          )
          .join("");

        const primaryCards = [
          {
            title: "Normalized composition",
            symbol: "xᵢ",
            units: "mole fraction",
            value: `<div class="composition-grid">${compositionItems}</div>`,
            isHtml: true,
          },
          {
            title: "Mixing entropy",
            symbol: "ΔS mix",
            units: "J/mol·K",
            value: formatNumber(descriptors.Smix),
          },
          {
            title: "Atomic size difference",
            symbol: "δ",
            units: "%",
            value: formatNumber(descriptors.delta),
          },
          {
            title: "Mean melting temperature",
            symbol: "Tm",
            units: `K (${formatNumber(descriptors.Tm_C)} °C)`,
            value: formatNumber(descriptors.Tm_K),
          },
          {
            title: "Mixing enthalpy",
            symbol: "ΔH mix",
            units: "kJ/mol",
            value: formatNumber(descriptors.Hmix),
          },
          {
            title: "Valence electron concentration",
            symbol: "VEC",
            units: "—",
            value: formatNumber(descriptors.VEC),
          },
          {
            title: "Omega parameter",
            symbol: "Ω",
            units: "—",
            value: formatNumber(descriptors.Omega),
          },
          {
            title: "Electronegativity mismatch",
            symbol: "Δχ",
            units: "Pauling",
            value: descriptors.delta_chi != null ? formatNumber(descriptors.delta_chi) : "—",
          },
          {
            title: "Mean electronegativity",
            symbol: "χ̄",
            units: "Pauling",
            value: descriptors.mean_chi != null ? formatNumber(descriptors.mean_chi) : "—",
          },
          {
            title: "Mismatch entropy",
            symbol: "S_E",
            units: "J/mol·K",
            value: descriptors.S_excess != null ? formatNumber(descriptors.S_excess) : "—",
          },
          {
            title: "Solid-solution Gibbs proxy",
            symbol: "ΔG SS",
            units: "kJ/mol",
            value: descriptors.DeltaG_ss != null ? formatNumber(descriptors.DeltaG_ss) : "—",
          },
          {
            title: "Most stable binary proxy",
            symbol: "ΔG max",
            units: "kJ/mol",
            value: descriptors.DeltaG_max != null ? formatNumber(descriptors.DeltaG_max) : "—",
          },
          {
            title: "King Phi",
            symbol: "Φ",
            units: "—",
            value: descriptors.Phi_king != null ? formatNumber(descriptors.Phi_king) : "—",
          },
          {
            title: "Ye phi",
            symbol: "φ",
            units: "—",
            value: descriptors.Phi_ye != null ? formatNumber(descriptors.Phi_ye) : "—",
          },
          {
            title: "Singh Lambda",
            symbol: "Λ",
            units: "J/mol·K·%²",
            value: descriptors.Lambda_singh != null ? formatNumber(descriptors.Lambda_singh) : "—",
          },
          {
            title: "Wang gamma",
            symbol: "γ",
            units: "—",
            value: descriptors.gamma_wang != null ? formatNumber(descriptors.gamma_wang) : "—",
          },
          {
            title: "Elastic-strain energy",
            symbol: "ΔH el",
            units: "kJ/mol",
            value: descriptors.H_elastic != null ? formatNumber(descriptors.H_elastic) : "—",
          },
        ];

        const miedemaCards = [];
        if (descriptors.H_compound !== null) {
          miedemaCards.push({
            title: "Compound enthalpy (Miedema+ASD)",
            symbol: "ΔH compound",
            units: "kJ/mol",
            value: formatNumber(descriptors.H_compound),
          });
        }
        if (descriptors.H_SS_total !== null) {
          miedemaCards.push(
            {
              title: "Solid solution enthalpy",
              symbol: "ΔH SS",
              units: "kJ/mol",
              value: formatNumber(descriptors.H_SS_total),
            },
            {
              title: "SS chemical contribution",
              symbol: "ΔH chem",
              units: "kJ/mol",
              value: formatNumber(descriptors.H_SS_chem),
            },
            {
              title: "SS elastic mismatch",
              symbol: "ΔH elast",
              units: "kJ/mol",
              value: formatNumber(descriptors.H_SS_elast),
            },
            {
              title: "SS structural contribution",
              symbol: "ΔH struct",
              units: "kJ/mol",
              value: formatNumber(descriptors.H_SS_struct),
            }
          );
        }
        if (descriptors.H_AM_total !== null) {
          miedemaCards.push(
            {
              title: "Amorphous enthalpy",
              symbol: "ΔH AM",
              units: "kJ/mol",
              value: formatNumber(descriptors.H_AM_total),
            },
            {
              title: "AM topological contribution",
              symbol: "ΔH topo",
              units: "kJ/mol",
              value: formatNumber(descriptors.H_AM_topo),
            }
          );
        }

        const [compositionCard, ...metricCards] = primaryCards;

        const compositionDiv = document.createElement("div");
        compositionDiv.className = "result-card composition-card";
        compositionDiv.innerHTML = `
          <h3>${compositionCard.title}</h3>
          <div class="symbol">${compositionCard.symbol || ""}</div>
          ${compositionCard.isHtml ? compositionCard.value : `<p>${compositionCard.value}</p>`}
          <div class="units">${compositionCard.units || ""}</div>
        `;
        resultsEl.appendChild(compositionDiv);

        metricCards.forEach((card) => {
          const div = document.createElement("div");
          div.className = "result-card";
          div.title = DESCRIPTOR_TIPS[card.title] || "";
          div.innerHTML = `
            <h3>${card.title}</h3>${provButtonHtml(card.title)}
            <div class="symbol">${card.symbol || ""}</div>
            ${card.isHtml ? card.value : `<p>${card.value}</p>`}
            <div class="units">${card.units || ""}</div>
          `;
          resultsEl.appendChild(div);
        });

        if (miedemaCards.length === 0) {
          miedemaPanelEl.classList.add("hidden");
        } else {
          miedemaPanelEl.classList.remove("hidden");
          miedemaCards.forEach((card) => {
            const div = document.createElement("div");
            div.className = "result-card result-card-compact";
            div.title = DESCRIPTOR_TIPS[card.title] || "";
            div.innerHTML = `
              <h3>${card.title}</h3>${provButtonHtml(card.title)}
              <div class="symbol">${card.symbol || ""}</div>
              <p>${card.value}</p>
              <div class="units">${card.units || ""}</div>
            `;
            miedemaResultsEl.appendChild(div);
          });
        }

        const ruleCards = [];
        ruleCards.push({
          title: "Yeh entropy rule",
          symbol: "ΔS mix vs 1.5R, R",
          units: descriptors.Smix != null ? `ΔS mix = ${formatNumber(descriptors.Smix)} J/mol·K` : "—",
          value: formatVerdict(rules.yeh_smix.verdict),
        });
        ruleCards.push({
          title: "Zhang size-mismatch rule",
          symbol: "δ < 6.5 % → single-phase",
          units: descriptors.delta != null ? `δ = ${formatNumber(descriptors.delta)} %` : "—",
          value: formatVerdict(rules.zhang_delta.verdict),
        });
        ruleCards.push({
          title: "Guo–Liu VEC rule",
          symbol: "VEC bounds 6.87, 8.0",
          units: descriptors.VEC != null ? `VEC = ${formatNumber(descriptors.VEC)}` : "—",
          value: formatVerdict(rules.guo_vec.verdict === "mixed" ? "mixed (FCC + BCC)" : rules.guo_vec.verdict),
          note: rules.guo_vec.note,
        });
        ruleCards.push({
          title: "Yang–Zhang Ω rule",
          symbol: "Ω > 1.1 → single-phase",
          units: descriptors.Omega != null ? `Ω = ${formatNumber(descriptors.Omega)}` : "—",
          value: formatVerdict(rules.yang_omega.verdict),
        });
        ruleCards.push({
          title: "King Phi rule",
          symbol: `Φ >= ${formatNumber(rules.king_phi.threshold, 4)} → solid solution`,
          units: descriptors.Phi_king != null ? `Φ = ${formatNumber(descriptors.Phi_king)} at T = ${formatNumber(descriptors.King_temperature_K, 5)} K` : "—",
          value: formatVerdict(rules.king_phi.verdict),
        });
        ruleCards.push({
          title: "Ye phi rule",
          symbol: `φ >= ${formatNumber(rules.ye_phi.threshold, 4)} → solid solution`,
          units: descriptors.Phi_ye != null ? `φ = ${formatNumber(descriptors.Phi_ye)}` : "—",
          value: formatVerdict(rules.ye_phi.verdict),
        });
        if (rules.senkov_kappa) {
          const kap = rules.senkov_kappa;
          ruleCards.push({
            title: "Senkov–Miracle kappa",
            symbol: kap.k1 != null ? `k₁ = ${formatNumber(kap.k1)} vs k₁ᶜʳ = ${formatNumber(kap.k1_cr)}` : "ΔG(SS) vs ΔG(IM), ΔS IM = 0.6·ΔS mix",
            units: kap.temperature != null ? `at T = ${formatNumber(kap.temperature, 5)} K` : "—",
            value: formatVerdict(kap.verdict),
            note: kap.note,
          });
        }
        if (rules.tsai_sigma) {
          ruleCards.push({
            title: "Tsai sigma window",
            symbol: "Cr/V and 6.88 ≤ VEC ≤ 7.84 → σ risk",
            units: descriptors.VEC != null ? `VEC = ${formatNumber(descriptors.VEC)}${rules.tsai_sigma.applies ? "" : ", no Cr/V"}` : "—",
            value: formatVerdict(rules.tsai_sigma.verdict === "not_applicable" ? "not applicable" : rules.tsai_sigma.verdict === "sigma_prone" ? "σ-prone (annealed)" : "σ unlikely"),
          });
        }
        if (rules.sheikh_ductility) {
          ruleCards.push({
            title: "Sheikh ductility screen",
            symbol: "VEC < 4.5 → ductile (bcc refractory)",
            units: descriptors.VEC != null ? `VEC = ${formatNumber(descriptors.VEC)}${rules.sheikh_ductility.applies ? "" : ", has non-refractory elements"}` : "—",
            value: formatVerdict(rules.sheikh_ductility.verdict === "not_applicable" ? "not applicable" : rules.sheikh_ductility.verdict),
          });
        }

        rulesPanelEl.classList.remove("hidden");
        ruleCards.forEach((card) => {
          const div = document.createElement("div");
          div.className = "result-card result-card-compact";
          div.title = DESCRIPTOR_TIPS[card.title] || "";
          div.innerHTML = `
            <h3>${card.title}</h3>${provButtonHtml(card.title)}
            <div class="symbol">${card.symbol || ""}</div>
            <p>${card.value}</p>
            <div class="units">${card.units || ""}</div>
            ${card.note ? `<div class="rule-note">${escapeHtmlText(card.note)}</div>` : ""}
          `;
          rulesEl.appendChild(div);
        });
      }

      function renderWarnings(warnings) {
        warningsEl.innerHTML = "";
        (warnings || []).forEach((warning) => {
          const li = document.createElement("li");
          li.textContent = warning;
          warningsEl.appendChild(li);
        });
      }

      function getPairKey(a, b) {
        return calcCore.pairKey(a, b);
      }

      /** Get the auto-computed default value for a pair. */
      function getDefaultPairEnthalpy(key) {
        if (Object.prototype.hasOwnProperty.call(calcCore.PAIR_ENTHALPIES, key)) {
          return { value: calcCore.PAIR_ENTHALPIES[key], source: "miedema" };
        }
        return null;
      }

      function renderPairEnthalpyEditor() {
        const { elements } = readComposition();
        const selected = elements.filter((el) => el && el !== CUSTOM_OPTION_VALUE);

        pairEnthalpyEditorEl.innerHTML = "";
        if (selected.length < 2) {
          pairEnthalpyEditorEl.innerHTML = `<div style="padding: 10px 12px; color: #64748b;">Select at least two elements to show pairs.</div>`;
          return;
        }
        if (selected.length !== elements.length) {
          pairEnthalpyEditorEl.innerHTML = `<div style="padding: 10px 12px; color: #64748b;">Fill all element selections to show unique pairs.</div>`;
          return;
        }
        const duplicates = selected.filter((item, index) => selected.indexOf(item) !== index);
        if (duplicates.length) {
          pairEnthalpyEditorEl.innerHTML = `<div style="padding: 10px 12px; color: #64748b;">Element selections must be unique to show pairs.</div>`;
          return;
        }

        const rows = [];
        for (let i = 0; i < selected.length; i += 1) {
          for (let j = i + 1; j < selected.length; j += 1) {
            const ei = selected[i];
            const ej = selected[j];
            const key = getPairKey(ei, ej);
            const edited = Object.prototype.hasOwnProperty.call(pairEnthalpyEdits, key)
              ? pairEnthalpyEdits[key]
              : undefined;
            const defaultInfo = getDefaultPairEnthalpy(key);
            const defaultVal = defaultInfo ? defaultInfo.value : undefined;
            const source = defaultInfo ? defaultInfo.source : null;
            const value = edited !== undefined ? edited : defaultVal;
            const placeholderVal = defaultVal !== undefined ? Number(defaultVal.toFixed(3)) : 0;

            let sourceLabel = "";
            if (edited !== undefined) {
              sourceLabel = `<span class="pair-source pair-source-manual" title="User-entered value">manual</span>`;
            } else if (source === "miedema") {
              sourceLabel = `<span class="pair-source pair-source-miedema" title="Miedema-model value: de Boer et al. (1988), digitized by matminer. The Element data view has its provenance.">Miedema</span>`;
            }

            rows.push(`
              <tr>
                <td>${ei}–${ej} ${sourceLabel}</td>
                <td>
                  <input
                    type="number"
                    step="0.001"
                    data-pair-key="${key}"
                    value="${value !== undefined ? Number(value.toFixed(3)) : ""}"
                    placeholder="${placeholderVal}"
                  />
                </td>
              </tr>
            `);
          }
        }

        pairEnthalpyEditorEl.innerHTML = `
          <table>
            <thead>
              <tr><th>Pair</th><th>ΔHᵢⱼ (kJ/mol)</th></tr>
            </thead>
            <tbody>${rows.join("")}</tbody>
          </table>
        `;
      }

      function calculateDescriptors(elements, fractions) {
        const sharedOptions = {
          elementData: ELEMENT_DATA,
          kingTemperature: getKingTemperatureOverride(),
          pairEnthalpyOverrides: pairEnthalpyEdits,
        };

        // Hmix/Omega and the phi-family descriptors all derive from the same
        // vendored pair-enthalpy table used by the Python library (hea_bench).
        const coreResult = calcCore.calculateDescriptors(fractions, sharedOptions);

        const warnings = [...new Set(coreResult.warnings || [])];
        const miedema = calculateMiedemaDescriptors(elements, fractions);
        if (miedema.warnings) warnings.push(...miedema.warnings);

        // Omega = Tm*Smix/|Hmix| diverges as Hmix -> 0, so its magnitude is
        // parametrization-sensitive for near-ideal alloys. Flag the regime.
        const hmixVal = coreResult.descriptors.Hmix;
        if (typeof hmixVal === "number" && isFinite(hmixVal) && Math.abs(hmixVal) < 2.0) {
          warnings.push(
            "|ΔHmix| is below 2 kJ/mol, so Ω diverges toward infinity and its " +
            "magnitude depends strongly on the Miedema pair-table parametrization. " +
            "Read Ω qualitatively here. The Ω > 1.1 verdict can be trusted, but the exact number cannot."
          );
        }

        const descriptors = {
          ...coreResult.descriptors,
          H_compound: miedema.compound ? miedema.compound.H_form : null,
          H_SS_total: miedema.solidSolution ? miedema.solidSolution.H_total : null,
          H_SS_chem: miedema.solidSolution ? miedema.solidSolution.H_chem : null,
          H_SS_elast: miedema.solidSolution ? miedema.solidSolution.H_elast : null,
          H_SS_struct: miedema.solidSolution ? miedema.solidSolution.H_struct : null,
          H_AM_total: miedema.amorphous ? miedema.amorphous.H_total : null,
          H_AM_chem: miedema.amorphous ? miedema.amorphous.H_chem : null,
          H_AM_topo: miedema.amorphous ? miedema.amorphous.H_topo : null,
        };

        return {
          descriptors,
          rules: calcCore.rulePredictionsFromDescriptors(descriptors, {
            kingThreshold: calcCore.KING_PHI_THRESHOLD,
            yeThreshold: calcCore.YE_PHI_THRESHOLD,
          }),
          warnings,
        };
      }

      function normalizePercents(percents) {
        const total = percents.reduce((sum, value) => sum + value, 0);
        if (total <= 0) {
          throw new Error("Total percentage must be greater than zero.");
        }
        return percents.map((p) => (p / total) * 100);
      }

      function handleEquimolar() {
        showError("");
        const inputs = ratioTableEl.querySelectorAll("input[data-percent-index]");
        if (inputs.length === 0) return;
        inputs.forEach((input) => { setPercent(input, 100 / inputs.length); });
        scheduleSaveFormState();
      }

      function handleNormalize() {
        showError("");
        const { percents } = readComposition();
        try {
          const normalized = normalizePercents(percents);
          ratioTableEl.querySelectorAll("input[data-percent-index]").forEach((input, idx) => {
            setPercent(input, normalized[idx]);
          });
          scheduleSaveFormState();
        } catch (error) {
          showError(error.message);
        }
      }

      // An error must not leave an earlier composition's results on screen
      // next to inputs they no longer describe.
      function showInputError(message) {
        showError(message);
        renderResults(null);
        renderWarnings([]);
        lastCalculation = null;
      }

      function handleCalculate() {
        showError("");
        showSaveMessage("");
        renderWarnings([]);
        const { elements, percents } = readComposition();
        const selected = elements.filter((el) => el);

        if (selected.length < 2) {
          showInputError("Select at least two elements.");
          return;
        }
        if (selected.length !== elements.length) {
          showInputError("Fill all element selections.");
          return;
        }
        if (selected.some((el) => el === CUSTOM_OPTION_VALUE)) {
          showInputError("Finish creating the custom element first.");
          openCustomPanel(null, null);
          return;
        }
        const duplicates = selected.filter((item, index) => selected.indexOf(item) !== index);
        if (duplicates.length) {
          showInputError("Each element can appear only once in the table. A formula such as CoCrFeNiNi adds repeats up for you.");
          return;
        }
        if (percents.some((p) => !Number.isFinite(p) || p <= 0)) {
          showInputError("All percentages must be positive numbers.");
          return;
        }

        let normalized;
        try {
          normalized = normalizePercents(percents);
        } catch (error) {
          showInputError(error.message);
          return;
        }

        ratioTableEl.querySelectorAll("input[data-percent-index]").forEach((input, idx) => {
          setPercent(input, normalized[idx]);
        });

        const fractions = Object.fromEntries(
          selected.map((el, idx) => [el, normalized[idx] / 100])
        );

        try {
          const { descriptors, rules, warnings } = calculateDescriptors(selected, fractions);
          renderResults({
            composition: fractions,
            descriptors,
            rules,
            coreOptions: { elementData: ELEMENT_DATA, pairEnthalpyOverrides: { ...pairEnthalpyEdits } },
          });
          renderWarnings(warnings);
          lastCalculation = {
            timestamp: Date.now(),
            elements: [...selected],
            percents: Object.fromEntries(selected.map((el, idx) => [el, normalized[idx]])),
            composition: { ...fractions },
            descriptors: { ...descriptors },
            rules: { ...rules },
          };
        } catch (error) {
          showInputError(error.message);
        }
      }

      function parseFormula(str) {
        // The one formula parser, shared with the library: repeated
        // elements add up, and (CoCrFeNi)95Al5 is 95 parts equimolar
        // CoCrFeNi plus 5 parts Al (parseFormula in hea-calculator-core.js).
        const parsed = calcCore.parseFormula(str);
        return Object.keys(parsed).map((symbol) => ({ symbol, percent: parsed[symbol] * 100 }));
      }

      // The last formula typed in; a permalink carries it while the table
      // still holds what it produced (buildShareUrl).
      let appliedFormula = null;

      function applyFormula() {
        showError("");
        const raw = formulaInput.value;
        let parsed;
        try {
          parsed = parseFormula(raw);
        } catch (e) {
          showInputError(e.message);
          return false;
        }
        const available = getAvailableElements();
        const unknown = parsed.filter(p => !available.includes(p.symbol));
        if (unknown.length) {
          showInputError(`Unknown element(s): ${unknown.map(u => u.symbol).join(", ")}`);
          return false;
        }
        if (parsed.length > 10) {
          showInputError(`The calculator takes up to 10 elements, and this formula has ${parsed.length}.`);
          return false;
        }
        const count = Math.min(10, Math.max(2, parsed.length));
        elementCountInput.value = count;
        renderRatioTable(count);
        const selects = ratioTableEl.querySelectorAll("select[data-element-index]");
        const inputs = ratioTableEl.querySelectorAll("input[data-percent-index]");
        parsed.forEach((p, i) => {
          selects[i].value = p.symbol;
          setPercent(inputs[i], p.percent);
        });
        appliedFormula = raw.trim();
        renderPairEnthalpyEditor();
        scheduleSaveFormState();
        return true;
      }

      function formulaStillApplies(elements, percents) {
        if (!appliedFormula) return false;
        let parsed;
        try {
          parsed = parseFormula(appliedFormula);
        } catch (e) {
          return false;
        }
        const total = percents.reduce((sum, p) => sum + p, 0);
        return parsed.length === elements.length && parsed.every((p, i) =>
          p.symbol === elements[i] && Math.abs(p.percent - (percents[i] / total) * 100) <= 1e-9 * p.percent);
      }

      function buildShareUrl() {
        const { elements, percents } = readComposition();
        const selected = elements.filter(el => el);
        if (selected.length < 2) return null;
        // The typed formula itself while the table still holds what it
        // produced, so the link reopens to the same composition the library
        // reads from that formula. Otherwise the table's exact amounts.
        const comp = formulaStillApplies(elements, percents)
          ? appliedFormula
          : selected.map((el, i) => `${el}${percents[i]}`).join("");
        const url = new URL(window.location.href.split("?")[0]);
        url.searchParams.set("comp", comp);
        const kingTemperature = getKingTemperatureOverride();
        if (kingTemperature !== null) {
          url.searchParams.set("kingT", String(kingTemperature));
        }
        return url.toString();
      }

      function applyUrlParams() {
        // Returns true when a permalink was applied, false when one was
        // present but rejected, and null when there was no permalink.
        const params = new URLSearchParams(window.location.search);
        const comp = params.get("comp");
        if (!comp) return null;
        // A ?comp= link is an alloy, whatever mode this browser used last.
        applyMode("alloy");
        const kingTemperature = Number(params.get("kingT"));
        formulaInput.value = comp;
        kingTemperatureInput.value = Number.isFinite(kingTemperature) && kingTemperature > 0 ? String(kingTemperature) : "";
        try {
          // applyFormula reports its own errors in the banner; a failed
          // parse must not fall through to computing whatever composition
          // happens to be left in the form (issue #1's permalink variant).
          if (!applyFormula()) return false;
          handleCalculate();
          return true;
        } catch (e) {
          return false;
        }
      }

      function loadExample() {
        const example = ["Cu", "Co", "Mn", "Ni", "Fe"];
        const examplePercents = [20, 20, 35, 20, 5];
        elementCountInput.value = example.length;
        renderRatioTable(example.length);
        ratioTableEl.querySelectorAll("select[data-element-index]").forEach((select, idx) => {
          select.value = example[idx];
        });
        ratioTableEl.querySelectorAll("input[data-percent-index]").forEach((input, idx) => {
          input.value = examplePercents[idx].toFixed(2);
        });
        renderPairEnthalpyEditor();
        scheduleSaveFormState();
      }

      function resetForm() {
        elementCountInput.value = 5;
        kingTemperatureInput.value = "";
        renderRatioTable(5);
        showError("");
        showSaveMessage("");
        renderResults(null);
        renderWarnings([]);
        pairEnthalpyEdits = {};
        savedResults = [];
        lastCalculation = null;
        closeCustomPanel();
        renderPairEnthalpyEditor();
        renderSavedResultsTable();
        clearSavedFormState();
        clearSavedResultsState();
      }

      function renderSavedResultsTable() {
        savedResultsBodyEl.innerHTML = "";
        if (!savedResults.length) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td colspan="20" style="color: #64748b;">No saved results yet.</td>`;
          savedResultsBodyEl.appendChild(tr);
          return;
        }

        savedResults.forEach((row) => {
          const tr = document.createElement("tr");
          const percentList = row.elements
            .map((e) => `${e}:${Number(row.percents[e]).toFixed(2)}`)
            .join(", ");
          tr.innerHTML = `
            <td>${row.elements.join("-")}</td>
            <td>${percentList}</td>
            <td>${formatNumber(row.descriptors.delta)}</td>
            <td>${formatNumber(row.descriptors.Tm_C)}</td>
            <td>${formatNumber(row.descriptors.Smix)}</td>
            <td>${formatNumber(row.descriptors.Hmix)}</td>
            <td>${formatNumber(row.descriptors.VEC)}</td>
            <td>${formatNumber(row.descriptors.Omega)}</td>
            <td>${row.descriptors.delta_chi != null ? formatNumber(row.descriptors.delta_chi) : '—'}</td>
            <td>${row.descriptors.S_excess != null ? formatNumber(row.descriptors.S_excess) : '—'}</td>
            <td>${row.descriptors.Phi_king != null ? formatNumber(row.descriptors.Phi_king) : '—'}</td>
            <td>${row.descriptors.Phi_ye != null ? formatNumber(row.descriptors.Phi_ye) : '—'}</td>
            <td>${row.descriptors.Lambda_singh != null ? formatNumber(row.descriptors.Lambda_singh) : '—'}</td>
            <td>${row.descriptors.gamma_wang != null ? formatNumber(row.descriptors.gamma_wang) : '—'}</td>
            <td>${row.descriptors.H_elastic != null ? formatNumber(row.descriptors.H_elastic) : '—'}</td>
            <td>${row.descriptors.King_temperature_K != null ? formatNumber(row.descriptors.King_temperature_K, 5) : '—'}</td>
            <td>${row.descriptors.H_compound != null ? formatNumber(row.descriptors.H_compound) : '—'}</td>
            <td>${row.descriptors.H_SS_total != null ? formatNumber(row.descriptors.H_SS_total) : '—'}</td>
            <td>${row.descriptors.H_AM_total != null ? formatNumber(row.descriptors.H_AM_total) : '—'}</td>
            <td><button class="ghost" data-delete-row="${row.id}">Delete</button></td>
          `;
          savedResultsBodyEl.appendChild(tr);
        });
      }

      function escapeCsvCell(value) {
        const text = String(value ?? "");
        if (/[",\n]/.test(text)) {
          return `"${text.replace(/"/g, '""')}"`;
        }
        return text;
      }


      function downloadCsv() {
        if (!savedResults.length) {
          showSaveMessage("Nothing to export.");
          return;
        }

        const header = [
          "Elements",
          "Composition (at. %)",
          "Atomic size difference (%)",
          "Mean melting temperature (°C)",
          "Mixing entropy (J/mol·K)",
          "Mixing enthalpy (kJ/mol)",
          "Valence electron concentration (—)",
          "Omega parameter (—)",
          "Electronegativity mismatch (Pauling)",
          "Mean electronegativity (Pauling)",
          "Mismatch entropy S_E (J/mol·K)",
          "King Phi (—)",
          "Ye phi (—)",
          "Singh Lambda (J/mol·K·%²)",
          "Wang gamma (—)",
          "Elastic-strain energy (kJ/mol)",
          "King temperature (K)",
          "Compound enthalpy (kJ/mol)",
          "SS enthalpy (kJ/mol)",
          "SS chemical (kJ/mol)",
          "SS elastic (kJ/mol)",
          "SS structural (kJ/mol)",
          "Amorphous enthalpy (kJ/mol)",
          "AM topological (kJ/mol)",
        ];
        const lines = [header.join(",")];

        savedResults.forEach((row) => {
          const percentsText = row.elements
            .map((e) => `${e}:${Number(row.percents[e]).toFixed(4)}`)
            .join(";");
          const line = [
            row.elements.join("-"),
            percentsText,
            row.descriptors.delta,
            row.descriptors.Tm_C,
            row.descriptors.Smix,
            row.descriptors.Hmix,
            row.descriptors.VEC,
            row.descriptors.Omega,
            row.descriptors.delta_chi ?? "",
            row.descriptors.mean_chi ?? "",
            row.descriptors.S_excess ?? "",
            row.descriptors.Phi_king ?? "",
            row.descriptors.Phi_ye ?? "",
            row.descriptors.Lambda_singh ?? "",
            row.descriptors.gamma_wang ?? "",
            row.descriptors.H_elastic ?? "",
            row.descriptors.King_temperature_K ?? "",
            row.descriptors.H_compound ?? "",
            row.descriptors.H_SS_total ?? "",
            row.descriptors.H_SS_chem ?? "",
            row.descriptors.H_SS_elast ?? "",
            row.descriptors.H_SS_struct ?? "",
            row.descriptors.H_AM_total ?? "",
            row.descriptors.H_AM_topo ?? "",
          ].map(escapeCsvCell);
          lines.push(line.join(","));
        });

        const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "hea_results.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }

      function saveCurrentResult() {
        if (!lastCalculation) {
          showSaveMessage("Run Calculate first.");
          return;
        }
        const row = {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          timestamp: Date.now(),
          elements: [...lastCalculation.elements],
          percents: { ...lastCalculation.percents },
          descriptors: { ...lastCalculation.descriptors },
        };
        savedResults.unshift(row);
        saveSavedResultsNow();
        renderSavedResultsTable();
        showSaveMessage("Saved.");
      }

      function deleteSavedRow(id) {
        savedResults = savedResults.filter((row) => row.id !== id);
        saveSavedResultsNow();
        renderSavedResultsTable();
      }

      elementCountInput.addEventListener("change", () => {
        const value = Math.min(10, Math.max(2, Number(elementCountInput.value) || 2));
        elementCountInput.value = value;
        renderRatioTable(value);
        renderPairEnthalpyEditor();
        scheduleSaveFormState();
      });
      calculateBtn.addEventListener("click", handleCalculate);
      loadExampleBtn.addEventListener("click", loadExample);
      equimolarBtn.addEventListener("click", handleEquimolar);
      normalizeBtn.addEventListener("click", handleNormalize);
      resetBtn.addEventListener("click", resetForm);
      parseFormulaBtn.addEventListener("click", applyFormula);
      formulaInput.addEventListener("keydown", (e) => { if (e.key === "Enter") applyFormula(); });
      shareUrlBtn.addEventListener("click", () => {
        const url = buildShareUrl();
        if (!url) { showError("Select at least two elements first."); return; }
        navigator.clipboard.writeText(url).then(() => {
          shareUrlBtn.textContent = "Copied!";
          setTimeout(() => { shareUrlBtn.textContent = "Copy URL"; }, 1500);
        }).catch(() => {
          showError("Failed to copy to clipboard.");
        });
      });

      ratioTableEl.addEventListener("change", (event) => {
        const target = event.target;
        if (target && target.matches && target.matches("select[data-element-index]")) {
          const idx = Number(target.getAttribute("data-element-index"));
          if (target.value === CUSTOM_OPTION_VALUE) {
            target.value = "";
            openCustomPanel(idx, null);
          }
          renderPairEnthalpyEditor();
          scheduleSaveFormState();
        }
      });

      ratioTableEl.addEventListener("input", (event) => {
        const target = event.target;
        if (!target || !target.matches) return;
        if (target.matches("input[data-percent-index]")) {
          scheduleSaveFormState();
        }
      });

      kingTemperatureInput.addEventListener("input", scheduleSaveFormState);

      // Enter anywhere in the alloy inputs runs the calculation.
      ratioTableEl.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && event.target.matches &&
            event.target.matches("input[data-percent-index]")) {
          handleCalculate();
        }
      });
      kingTemperatureInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") handleCalculate();
      });

      // ---------------------------------------------------------------
      // Oxides mode: high-entropy-oxide descriptors via the same
      // parity-tested core (describeRockSalt/Perovskite/Fluorite/
      // Pyrochlore). The mode switch only toggles which panels are
      // visible; both modes keep their state.

      const MODE_STORAGE_KEY = "hea-bench-mode";
      const modeSwitchEl = document.getElementById("mode-switch");
      const oxideFamilyEl = document.getElementById("oxide-family");
      const oxideExampleEl = document.getElementById("oxide-example");
      const oxideAInput = document.getElementById("oxide-a-site");
      const oxideBInput = document.getElementById("oxide-b-site");
      const oxideALabel = document.getElementById("oxide-a-label");
      const oxideBLabel = document.getElementById("oxide-b-label");
      const oxideBRow = document.getElementById("oxide-b-row");
      const oxideOxygenRow = document.getElementById("oxide-oxygen-row");
      const oxideOxygenInput = document.getElementById("oxide-oxygen");
      const oxideSpinEl = document.getElementById("oxide-spin");
      const oxideCalculateBtn = document.getElementById("oxide-calculate");
      const oxideResultsEl = document.getElementById("oxide-results");
      const oxideVerdictsPanelEl = document.getElementById("oxide-verdicts-panel");
      const oxideVerdictsEl = document.getElementById("oxide-verdicts");
      const oxideCopyBtn = document.getElementById("oxide-copy-json");
      let lastOxideReport = null;

      const OXIDE_FAMILY_CONFIG = {
        rock_salt: { aLabel: "Cations (six-fold)", twoSite: false, oxygenInput: false },
        perovskite: {
          aLabel: "A-site cations (twelve-fold)",
          bLabel: "B-site cations (six-fold)",
          twoSite: true,
          oxygenInput: false,
        },
        fluorite: { aLabel: "Cations (eight-fold)", twoSite: false, oxygenInput: true },
        pyrochlore: {
          aLabel: "A-site cations (eight-fold)",
          bLabel: "B-site cations (six-fold)",
          twoSite: true,
          oxygenInput: false,
        },
      };

      const OXIDE_FAMILY_LABELS = {
        rock_salt: "Rock salt (MO)",
        perovskite: "Perovskite (ABO₃)",
        fluorite: "Fluorite (MOₓ)",
        pyrochlore: "Pyrochlore (A₂B₂O₇)",
      };

      const OXIDE_EXAMPLES = {
        j14: { family: "rock_salt", a: "MgCoNiCuZn" },
        jiang: { family: "perovskite", a: "Sr", b: "ZrSnTiHfMn" },
        feso_low: { family: "fluorite", a: "CeZrNdYEr", oxygen: "1.70" },
        feso_high: { family: "fluorite", a: "CeZrLaNdSm", oxygen: "1.70" },
        pyro: { family: "pyrochlore", a: "LaCeNdSmEu", b: "Zr" },
      };

      function applyMode(mode) {
        document.body.classList.toggle("mode-oxide", mode === "oxide");
        document.body.classList.toggle("mode-ceramic", mode === "ceramic");
        modeSwitchEl.querySelectorAll(".mode-btn").forEach((btn) => {
          btn.classList.toggle("is-active", btn.getAttribute("data-mode") === mode);
        });
        showError("");
        try { localStorage.setItem(MODE_STORAGE_KEY, mode); } catch (e) { /* storage unavailable */ }
      }

      function applyOxideFamily() {
        const cfg = OXIDE_FAMILY_CONFIG[oxideFamilyEl.value];
        oxideALabel.textContent = cfg.aLabel;
        oxideBRow.classList.toggle("hidden", !cfg.twoSite);
        if (cfg.twoSite) oxideBLabel.textContent = cfg.bLabel;
        oxideOxygenRow.classList.toggle("hidden", !cfg.oxygenInput);
      }

      function readOxideSite(inputEl, label) {
        let parsed;
        try {
          parsed = parseFormula(inputEl.value);
        } catch (e) {
          throw new Error(`${label}: ${e.message}`);
        }
        const site = {};
        parsed.forEach((p) => { site[p.symbol] = (site[p.symbol] || 0) + p.percent; });
        const unknown = Object.keys(site).filter((el) => !calcCore.OXIDE_ELEMENT_DATA[el]);
        if (unknown.length) {
          throw new Error(
            `${label}: no oxide data for ${unknown.join(", ")} (not in the Shannon radius table).`
          );
        }
        return site;
      }

      function handleOxideCalculate() {
        showError("");
        const family = oxideFamilyEl.value;
        const cfg = OXIDE_FAMILY_CONFIG[family];
        const options = { spin: oxideSpinEl.value };
        let report;
        try {
          const aSite = readOxideSite(oxideAInput, cfg.twoSite ? "A-site" : "Cations");
          if (cfg.oxygenInput) {
            const oxygen = Number(oxideOxygenInput.value);
            if (!Number.isFinite(oxygen) || oxygen <= 0) {
              throw new Error("Oxygen per formula unit must be a positive number.");
            }
            options.oxygen = oxygen;
          }
          if (cfg.twoSite) {
            const bSite = readOxideSite(oxideBInput, "B-site");
            report = family === "perovskite"
              ? calcCore.describePerovskite(aSite, bSite, options)
              : calcCore.describePyrochlore(aSite, bSite, options);
          } else {
            report = family === "rock_salt"
              ? calcCore.describeRockSalt(aSite, options)
              : calcCore.describeFluorite(aSite, options);
          }
        } catch (e) {
          showError(e.message);
          return;
        }
        lastOxideReport = report;
        renderOxideReport(report);
        renderWarnings(report.warnings);
      }

      function oxideChargeSup(q) {
        return q >= 0 ? `${q}+` : `${-q}−`;
      }

      function oxideMetricCard(title, symbol, value, units) {
        return { title, symbol, value, units };
      }

      function renderOxideReport(report) {
        provRememberOxide(report);
        renderCitePanel("oxide");
        oxideResultsEl.innerHTML = "";
        oxideVerdictsEl.innerHTML = "";

        const siteBlocks = Object.keys(report.sites).map((siteLabel) => {
          const cells = Object.entries(report.sites[siteLabel]).map(([el, frac]) => {
            const charge = report.oxidation_states[el];
            const radius = report.shannon_radii[el];
            return `<div class="composition-cell">` +
              `<div class="element">${el}<sup>${oxideChargeSup(charge)}</sup></div>` +
              `<div class="fraction">${formatNumber(frac, 4)}</div>` +
              `<div class="fraction" style="opacity: 0.7;">${formatNumber(radius, 4)} Å</div>` +
              `</div>`;
          }).join("");
          const siteName = siteLabel === "M" ? "Cation site" : `${siteLabel} site`;
          return `<div style="margin-bottom: 6px;">` +
            `<div class="units" style="margin-bottom: 4px;">${siteName} · CN ${report.coordination[siteLabel]}</div>` +
            `<div class="composition-grid">${cells}</div></div>`;
        }).join("");

        const headerCard = document.createElement("div");
        headerCard.className = "result-card composition-card";
        headerCard.innerHTML = `
          <h3>${OXIDE_FAMILY_LABELS[report.family]}</h3>
          <div class="symbol">site fractions, assigned oxidation states, Shannon radii</div>
          ${siteBlocks}
          <div class="units">oxygen per formula unit: ${formatNumber(report.oxygen_per_formula_unit, 4)}</div>
        `;
        oxideResultsEl.appendChild(headerCard);

        const d = report.descriptors;
        const cards = [
          oxideMetricCard("Configurational entropy", "ΔS config", formatNumber(d.s_config), "J/mol·K per formula unit"),
          oxideMetricCard("Entropy per cation site", "ΔS config / cation", formatNumber(d.s_config_per_cation), "J/mol·K"),
        ];
        if (d.delta_r !== undefined) {
          cards.push(oxideMetricCard("Cation size disorder", "δr", formatNumber(d.delta_r), "%"));
          cards.push(oxideMetricCard("Mean cation radius", "r̄", formatNumber(d.mean_radius), "Å"));
        }
        if (d.delta_r_a !== undefined) {
          cards.push(oxideMetricCard("A-site size disorder", "δr(A)", formatNumber(d.delta_r_a), "%"));
          cards.push(oxideMetricCard("B-site size disorder", "δr(B)", formatNumber(d.delta_r_b), "%"));
          cards.push(oxideMetricCard("Combined size disorder", "δr*", formatNumber(d.delta_r_star), "%"));
          cards.push(oxideMetricCard("Mean A-site radius", "r̄(A)", formatNumber(d.mean_radius_a), "Å"));
          cards.push(oxideMetricCard("Mean B-site radius", "r̄(B)", formatNumber(d.mean_radius_b), "Å"));
        }
        if (d.radius_sigma !== undefined && d.radius_sigma !== null) {
          cards.push(oxideMetricCard("Radius dispersion (sample SD)", "σ(r)", formatNumber(d.radius_sigma), "Å, eight-fold radii"));
        }
        if (d.goldschmidt_t !== undefined) {
          cards.push(oxideMetricCard("Goldschmidt tolerance factor", "t", formatNumber(d.goldschmidt_t), "—"));
          cards.push(oxideMetricCard("Octahedral factor", "μ", formatNumber(d.octahedral_mu), "—"));
          if (d.bartel_tau !== null) {
            cards.push(oxideMetricCard("Bartel tolerance factor", "τ", formatNumber(d.bartel_tau), "—"));
          }
        }
        if (d.radius_ratio !== undefined) {
          cards.push(oxideMetricCard("Radius ratio", "r(A)/r(B)", formatNumber(d.radius_ratio), "—"));
        }
        if (d.mean_chi !== null) {
          cards.push(oxideMetricCard("Mean cation electronegativity", "χ̄", formatNumber(d.mean_chi), "Pauling"));
          cards.push(oxideMetricCard("Electronegativity mismatch", "Δχ", formatNumber(d.delta_chi), "Pauling"));
        }
        cards.forEach((card) => {
          const div = document.createElement("div");
          div.className = "result-card";
          div.title = DESCRIPTOR_TIPS[card.title] || "";
          div.innerHTML = `
            <h3>${card.title}</h3>${provButtonHtml(card.title)}
            <div class="symbol">${card.symbol}</div>
            <p>${card.value}</p>
            <div class="units">${card.units}</div>
          `;
          oxideResultsEl.appendChild(div);
        });

        const verdictCards = [];
        const entropyText = {
          "high-entropy": ["High entropy", "most-disordered sublattice ≥ 1.5R"],
          "medium-entropy": ["Medium entropy", "most-disordered sublattice between 1.36R and 1.5R"],
          "low-entropy": ["Low entropy", "most-disordered sublattice < 1.36R"],
        }[report.verdicts.entropy];
        verdictCards.push(oxideMetricCard("Entropy classification", "ΔS vs 1.5R", entropyText[0], entropyText[1]));
        if (report.verdicts.spiridigliozzi) {
          const isFluorite = report.verdicts.spiridigliozzi === "fluorite";
          verdictCards.push(oxideMetricCard(
            "Spiridigliozzi radius-dispersion rule",
            "σ(r) > 0.095 Å → fluorite",
            isFluorite ? "Single-phase fluorite favored" : "Bixbyite-type or mixed phases likely",
            `σ(r) = ${formatNumber(d.radius_sigma)} Å (rule calibrated on equimolar rare-earth oxides)`
          ));
        }
        if (report.verdicts.goldschmidt) {
          const windowText = {
            "within-window": "Inside the cubic window",
            "below-window": "Below the window: tilted (orthorhombic) distortion likely",
            "above-window": "Above the window: hexagonal stacking likely",
          }[report.verdicts.goldschmidt];
          verdictCards.push(oxideMetricCard(
            "Goldschmidt window",
            "0.92 ≤ t ≤ 1.04",
            windowText,
            `t = ${formatNumber(d.goldschmidt_t)}`
          ));
          const octText = {
            "within-window": "Stable BO₆ octahedron",
            "below-window": "B cation too small for a stable octahedron",
            "above-window": "B cation too large for a stable octahedron",
          }[report.verdicts.octahedral];
          verdictCards.push(oxideMetricCard(
            "Octahedral window",
            "0.414 < μ < 0.732",
            octText,
            `μ = ${formatNumber(d.octahedral_mu)}`
          ));
          if (report.verdicts.bartel) {
            verdictCards.push(oxideMetricCard(
              "Bartel τ rule",
              "τ < 4.18 → perovskite",
              report.verdicts.bartel === "perovskite" ? "Perovskite predicted" : "Non-perovskite predicted",
              `τ = ${formatNumber(d.bartel_tau)} (~91% reported accuracy)`
            ));
          }
        }
        if (report.verdicts.radius_ratio) {
          const ratioText = {
            "pyrochlore": "Pyrochlore window",
            "defect-fluorite": "Defect fluorite likely (ratio below 1.46)",
            "no-single-cubic-phase": "No single cubic phase expected (ratio above 1.78)",
          }[report.verdicts.radius_ratio];
          verdictCards.push(oxideMetricCard(
            "Pyrochlore radius-ratio rule",
            "1.46 < r(A)/r(B) < 1.78",
            ratioText,
            `r(A)/r(B) = ${formatNumber(d.radius_ratio)}`
          ));
        }
        oxideVerdictsPanelEl.classList.remove("hidden");
        verdictCards.forEach((card) => {
          const div = document.createElement("div");
          div.className = "result-card result-card-compact";
          div.innerHTML = `
            <h3>${card.title}</h3>
            <div class="symbol">${card.symbol}</div>
            <p>${card.value}</p>
            <div class="units">${card.units}</div>
          `;
          oxideVerdictsEl.appendChild(div);
        });
      }

      modeSwitchEl.addEventListener("click", (event) => {
        const btn = event.target.closest(".mode-btn");
        if (btn) applyMode(btn.getAttribute("data-mode"));
      });
      oxideFamilyEl.addEventListener("change", applyOxideFamily);
      oxideExampleEl.addEventListener("change", () => {
        const example = OXIDE_EXAMPLES[oxideExampleEl.value];
        oxideExampleEl.value = "";
        if (!example) return;
        oxideFamilyEl.value = example.family;
        applyOxideFamily();
        oxideAInput.value = example.a;
        oxideBInput.value = example.b || "";
        oxideOxygenInput.value = example.oxygen || "2.00";
        handleOxideCalculate();
      });
      oxideCalculateBtn.addEventListener("click", handleOxideCalculate);
      [oxideAInput, oxideBInput, oxideOxygenInput].forEach((el) => {
        el.addEventListener("keydown", (event) => {
          if (event.key === "Enter") handleOxideCalculate();
        });
      });
      oxideCopyBtn.addEventListener("click", () => {
        if (!lastOxideReport) return;
        // Same receipt envelope as the cite panel; the raw report rides
        // in receipt.outputs so earlier consumers keep their fields.
        const payload = citeState && citeState.mode === "oxide" ? citeState.receipt : lastOxideReport;
        navigator.clipboard.writeText(JSON.stringify(payload, null, 2)).then(() => {
          oxideCopyBtn.textContent = "Copied!";
          setTimeout(() => { oxideCopyBtn.textContent = "Copy report (JSON)"; }, 1500);
        }).catch(() => {
          showError("Failed to copy to clipboard.");
        });
      });

      applyOxideFamily();
      let storedMode = "alloy";
      try { storedMode = localStorage.getItem(MODE_STORAGE_KEY) || "alloy"; } catch (e) { /* storage unavailable */ }
      if (storedMode === "oxide" || storedMode === "ceramic") applyMode(storedMode);

      // ---------------------------------------------------------------
      // 1.6.1 polish: descriptor tooltips, click-to-copy cards, theme
      // toggle, what's-new popover, welcome quick-start, Ctrl+Enter.

      const DESCRIPTOR_TIPS = {
        "Mixing entropy": "Ideal configurational entropy, −R Σ xᵢ ln xᵢ. At or above 1.5R is the usual high-entropy threshold.",
        "Atomic size difference": "Composition-weighted spread of atomic radii. Values above about 6.5% work against a single-phase solid solution.",
        "Mean melting temperature": "Rule-of-mixtures average of the elemental melting points.",
        "Mixing enthalpy": "Miedema-model estimate. The model is semi-empirical, and pairs involving Mn carry the largest parametrization uncertainty.",
        "Valence electron concentration": "Weighted mean valence-electron count. At or above 8 favors FCC, below 6.87 favors BCC.",
        "Omega parameter": "Tm·ΔSmix / |ΔHmix| (Yang and Zhang). Above 1.1 favors a solid solution. Diverges as ΔHmix approaches zero, so read it qualitatively there.",
        "Electronegativity mismatch": "Composition-weighted standard deviation of Pauling electronegativities. Large values favor ordered compounds.",
        "Mean electronegativity": "Composition-weighted mean Pauling electronegativity.",
        "Mismatch entropy": "Mansoori hard-sphere excess entropy from the size distribution. It feeds the Ye phi index.",
        "Solid-solution Gibbs proxy": "ΔHmix − T·ΔSmix at the chosen temperature. More negative means a more stable disordered solution.",
        "Most stable binary proxy": "Most negative raw pair enthalpy ΔHᵢⱼ over all pairs, with no composition scaling, a proxy for the strongest competing binary compound.",
        "King Phi": "Ratio of the solid-solution driving force to the strongest competing binary (King 2016). Above 1 predicts a stable solid solution.",
        "Ye phi": "Single-parameter index combining mixing entropy, mismatch entropy, and enthalpy (Ye 2015). Above about 20 predicts a solid solution.",
        "Compound enthalpy (Miedema+ASD)": "Ordered-compound formation enthalpy from the Miedema model with the structural-stability correction.",
        "Solid solution enthalpy": "Disordered solid-solution formation enthalpy: chemical plus elastic plus structural terms.",
        "SS chemical contribution": "Miedema chemical interaction term of the solid-solution enthalpy.",
        "SS elastic mismatch": "Continuum elastic-strain energy from atomic size mismatch.",
        "SS structural contribution": "Lattice-stability term from the valence-electron dependence of the bcc/fcc/hcp energies.",
        "Amorphous enthalpy": "Amorphous-phase formation enthalpy: chemical term plus a topological term.",
        "AM topological contribution": "Topological term of the amorphous-phase enthalpy, proportional to the mean melting temperature.",
        "Yeh entropy rule": "ΔSmix at or above 1.5R counts as a high-entropy alloy (Yeh 2004). From 1R to 1.5R the alloy is medium entropy.",
        "Zhang size-mismatch rule": "Single phase predicted when δ is below 6.5% (Zhang 2008).",
        "Guo–Liu VEC rule": "FCC at VEC ≥ 8, BCC below 6.87, mixed in between (Guo and Liu 2011).",
        "Yang–Zhang Ω rule": "Solid solution predicted when Ω is above 1.1 (Yang and Zhang 2012).",
        "King Phi rule": "Solid solution predicted when Φ is at least 1 at the chosen temperature (King 2016).",
        "Ye phi rule": "Solid solution predicted when φ is at least 20 (Ye 2015).",
        "Configurational entropy": "Sublattice-weighted ideal mixing entropy per mole of formula units. Fully ordered sublattices contribute zero.",
        "Entropy per cation site": "The same entropy divided by the number of cation sites. The 1.5R threshold applies to this value.",
        "Cation size disorder": "Weighted spread of Shannon ionic radii on the cation sublattice, the ionic analog of the alloy δ.",
        "Mean cation radius": "Composition-weighted mean Shannon radius at the family's coordination number.",
        "A-site size disorder": "Size-disorder parameter of the A sublattice from Shannon radii.",
        "B-site size disorder": "Size-disorder parameter of the B sublattice from Shannon radii.",
        "Combined size disorder": "Square root of the sum of the squared per-sublattice size disorders.",
        "Mean A-site radius": "Composition-weighted mean Shannon radius of the A sublattice.",
        "Mean B-site radius": "Composition-weighted mean Shannon radius of the B sublattice.",
        "Radius dispersion (sample SD)": "Sample standard deviation of the eight-fold cation radii, the input of the Spiridigliozzi fluorite predictor.",
        "Goldschmidt tolerance factor": "(r̄A + rO) / √2(r̄B + rO). Cubic perovskites cluster near t = 1.",
        "Octahedral factor": "r̄B / rO. A stable BO₆ octahedron needs a value between 0.414 and 0.732.",
        "Bartel tolerance factor": "Improved perovskite tolerance factor (Bartel 2019). A value below 4.18 predicts a perovskite.",
        "Radius ratio": "Mean A radius over mean B radius. Pyrochlores form between 1.46 and 1.78.",
        "Mean cation electronegativity": "Composition-weighted mean Pauling electronegativity over all cations.",
        "Singh Lambda": "ΔSmix / δ² with δ in percent. Above 0.96 favors a single disordered solid solution (Singh 2014).",
        "Wang gamma": "Solid-angle packing ratio around the smallest vs largest atom. Below 1.175 the mismatch is packable as a crystalline solid solution (Wang 2015).",
        "Elastic-strain energy": "Andreoli 2019 elastic-strain energy from bulk moduli and atomic volumes. fcc solid solutions cluster below 6.05 kJ/mol, bcc between 6.05 and 22.",
        "Senkov–Miracle kappa": "Compares ΔG of the solid solution against the most stable binary compound at an explicit temperature, with ΔS(IM) = 0.6·ΔSmix (Senkov and Miracle 2016).",
        "Tsai sigma window": "Annealed Cr- or V-containing alloys with 6.88 ≤ VEC ≤ 7.84 tend to precipitate the sigma phase (Tsai 2013).",
        "Sheikh ductility screen": "For single-phase bcc refractory HEAs made only of Ti, Zr, Hf, V, Nb, Ta, Cr, Mo and W: VEC below 4.5 predicts intrinsic ductility (Sheikh 2016). Not applicable to any other alloy.",
      };

      // ---- Provenance drawer -----------------------------------------
      // One registry entry per result-card title: the defining equation,
      // which inputs the number consumed, the interpretation window with
      // its primary sources, and cross-links into Theory / Equations /
      // References / Data. The drawer renders registry + live payload.

      const PROV_REGISTRY = {
        "Mixing entropy": { sym: "ΔS mix", eq: "\\Delta S_{\\mathrm{mix}} = -R\\sum_i c_i \\ln c_i", inputs: ["composition"], interp: "Ideal configurational entropy. Yeh's classes: ≥ 1.5R high entropy, 1R–1.5R medium, below 1R dilute.", refs: ["yeh2004"], theory: "sec-entropy", eqn: "eq-smix" },
        "Atomic size difference": { sym: "δ", eq: "\\delta = 100\\sqrt{\\textstyle\\sum_i c_i\\,(1 - r_i/\\bar r)^2}", inputs: ["radius"], interp: "Zhang's single-phase window is δ < 6.5 %. The phase-selection maps draw the joint (δ, ΔH mix) windows.", refs: ["zhang2008"], theory: "sec-delta", eqn: "eq-delta" },
        "Mean melting temperature": { sym: "Tm", eq: "T_m = \\sum_i c_i\\,T_{m,i}", inputs: ["melting"], interp: "Rule-of-mixtures average. It feeds Ω and is the default annealing temperature for King Φ and κ.", refs: ["crc", "yang2012"], theory: "sec-omega", eqn: "eq-omega" },
        "Mixing enthalpy": { sym: "ΔH mix", eq: "\\Delta H_{\\mathrm{mix}} = \\sum_{i<j} 4\\,c_i c_j\\,\\Delta H^{\\mathrm{mix}}_{ij}", inputs: ["pairs"], interp: "Regular-solution estimate over Miedema binary enthalpies. The model is semi-empirical, and pairs involving Mn carry the largest parametrization uncertainty.", refs: ["takeuchi2005", "deboer1988", "matminer2018"], theory: "sec-hmix", eqn: "eq-hmix" },
        "Valence electron concentration": { sym: "VEC", eq: "\\mathrm{VEC} = \\sum_i c_i\\,\\mathrm{VEC}_i", inputs: ["valence"], interp: "Guo's bands: FCC at VEC ≥ 8, BCC below 6.87, mixed between. Read it only after a solid-solution verdict.", refs: ["guo2011vec"], theory: "sec-vec", eqn: "eq-vec" },
        "Omega parameter": { sym: "Ω", eq: "\\Omega = \\dfrac{T_m\\,\\Delta S_{\\mathrm{mix}}}{|\\Delta H_{\\mathrm{mix}}|}", inputs: ["melting", "pairs"], interp: "Ω ≥ 1.1 favors the entropy-stabilized solid solution. Diverges as ΔH mix → 0, so treat huge values qualitatively.", refs: ["yang2012"], theory: "sec-omega", eqn: "eq-omega" },
        "Electronegativity mismatch": { sym: "Δχ", eq: "\\Delta\\chi = \\sqrt{\\textstyle\\sum_i c_i\\,(\\chi_i - \\bar\\chi)^2}", inputs: ["chi"], interp: "Large values favor ordered compounds. For oxides the same statistic runs over the cation set.", refs: ["pauling1960"], theory: null, eqn: "eq-chi" },
        "Mean electronegativity": { sym: "χ̄", eq: "\\bar\\chi = \\sum_i c_i\\,\\chi_i", inputs: ["chi"], interp: "Composition-weighted mean of the Pauling set.", refs: ["pauling1960"], theory: null, eqn: "eq-chi" },
        "Mismatch entropy": { sym: "S_E", eq: null, inputs: ["radius"], interp: "Mansoori hard-sphere excess entropy from the diameter distribution, averaged over bcc (0.68) and fcc (0.74) packing fractions. Ye's φ uses it as the denominator.", refs: ["mansoori1971", "takeuchi2000"], theory: null, eqn: null },
        "Solid-solution Gibbs proxy": { sym: "ΔG SS", eq: "\\Delta G_{\\mathrm{ss}} = \\Delta H_{\\mathrm{mix}} - T\\,\\Delta S_{\\mathrm{mix}}", inputs: ["pairs", "temperature"], interp: "Gibbs energy of the disordered solution at the chosen temperature.", refs: ["king2016"], theory: "sec-prediction", eqn: null },
        "Most stable binary proxy": { sym: "ΔG max", eq: null, inputs: ["pairs"], interp: "The most negative binary pair enthalpy, standing in for the most stable competing intermetallic (King's ΔS ≈ 0 assumption). Documented approximation: it underestimates King's multi-binary allocation for 4+ elements, so Φ here runs larger than the paper's scale.", refs: ["king2016", "takeuchi2005"], theory: "sec-prediction", eqn: null },
        "King Phi": { sym: "Φ", eq: "\\Phi = \\dfrac{\\Delta G_{\\mathrm{ss}}}{-|\\Delta G_{\\mathrm{max}}|}", inputs: ["pairs", "temperature"], interp: "Φ > 1 suggests the solid solution beats the best binary compound at the chosen temperature. Carries the ΔG max approximation noted on that card.", refs: ["king2016"], theory: "sec-prediction", eqn: null },
        "Ye phi": { sym: "φ", eq: "\\varphi = \\dfrac{\\Delta S_{\\mathrm{mix}} - |\\Delta H_{\\mathrm{mix}}|/T_m}{|S_E|}", inputs: ["pairs", "melting", "radius"], interp: "Intrinsic-entropy screen. φ > 20 favors single-phase solid solutions.", refs: ["ye2015phi", "mansoori1971"], theory: "sec-prediction", eqn: null },
        "Singh Lambda": { sym: "Λ", eq: "\\Lambda = \\dfrac{\\Delta S_{\\mathrm{mix}}}{\\delta^2}", inputs: ["radius"], interp: "Λ > 0.96 means a single disordered solid solution, 0.24–0.96 means solid solution plus compounds, and below 0.24 compounds dominate. δ enters in percent.", refs: ["singh2014"], theory: "sec-geometry", eqn: "eq-lambda" },
        "Wang gamma": { sym: "γ", eq: "\\omega(r_c) = 1 - \\sqrt{\\dfrac{(r_c+\\bar r)^2 - \\bar r^2}{(r_c+\\bar r)^2}},\\quad \\gamma = \\dfrac{\\omega_S}{\\omega_L}", inputs: ["radius"], interp: "γ < 1.175 means the size mismatch is still packable as a crystalline solid solution. Equal radii give exactly 1.", refs: ["wang2015"], theory: "sec-geometry", eqn: "eq-gamma-wang" },
        "Elastic-strain energy": { sym: "ΔH el", eq: "\\Delta H_{\\mathrm{el}} = \\sum_i \\dfrac{c_i B_i (V_i - \\bar V)^2}{2 V_i},\\quad \\bar V = \\dfrac{\\sum_i c_i B_i V_i}{\\sum_i c_i B_i}", inputs: ["mechanics"], interp: "Andreoli's windows: fcc solid solutions ≤ 6.05 kJ/mol, bcc 6.05–22, above 22 glasses and intermetallics. The B and V values here come from the vendored matminer table, which differs from the paper's elastic sources, so read the window, not the third decimal.", refs: ["andreoli2019"], theory: "sec-elastic", eqn: "eq-hel" },
        "Compound enthalpy (Miedema+ASD)": { sym: "ΔH compound", eq: null, inputs: ["miedema-params"], interp: "Ordered-compound formation enthalpy from the Miedema macroscopic-atom model with the atomic-size-difference correction.", refs: ["miedema1980", "deboer1988"], theory: "sec-compound", eqn: "eq-compound" },
        "Solid solution enthalpy": { sym: "ΔH SS", eq: null, inputs: ["miedema-params", "mechanics"], interp: "Chemical + elastic + structural decomposition of the disordered solution's formation enthalpy.", refs: ["deboer1988", "eshelby1957", "friedel1954"], theory: "sec-ss", eqn: "eq-ssmied" },
        "SS chemical contribution": { sym: "ΔH chem", eq: null, inputs: ["miedema-params"], interp: "Miedema interfacial term of the solid-solution enthalpy.", refs: ["miedema1980", "deboer1988"], theory: "sec-ss", eqn: "eq-ssmied" },
        "SS elastic mismatch": { sym: "ΔH elast", eq: null, inputs: ["mechanics"], interp: "Continuum (Eshelby/Friedel) size-mismatch strain term.", refs: ["eshelby1957", "deboer1988"], theory: "sec-ss", eqn: "eq-elast" },
        "SS structural contribution": { sym: "ΔH struct", eq: null, inputs: ["valence"], interp: "d-band lattice-stability term from the valence-electron counts.", refs: ["friedel1954", "niessen1983"], theory: "sec-ss", eqn: null },
        "Amorphous enthalpy": { sym: "ΔH AM", eq: null, inputs: ["miedema-params", "melting"], interp: "Amorphous-phase enthalpy: chemical term plus the topological 3.5·Σcᵢ T m,i correction.", refs: ["loeff1988", "deboer1988"], theory: "sec-am", eqn: "eq-am" },
        "AM topological contribution": { sym: "ΔH topo", eq: null, inputs: ["melting"], interp: "The 3.5·Σcᵢ T m,i topological term of the amorphous enthalpy.", refs: ["loeff1988"], theory: "sec-am", eqn: "eq-am" },
        "Yeh entropy rule": { sym: "ΔS mix vs R", eq: null, inputs: ["composition"], interp: "≥ 1.5R high entropy, 1R–1.5R medium entropy, below dilute. A definition, not a phase prediction.", refs: ["yeh2004"], theory: "sec-entropy", eqn: "eq-smix" },
        "Zhang size-mismatch rule": { sym: "δ < 6.5 %", eq: null, inputs: ["radius"], interp: "Single phase predicted below 6.5 %. The screen is empirical, calibrated on the 2008 survey.", refs: ["zhang2008"], theory: "sec-delta", eqn: "eq-delta" },
        "Guo–Liu VEC rule": { sym: "VEC bands", eq: null, inputs: ["valence"], interp: "FCC at VEC ≥ 8, BCC below 6.87. Says which lattice a solid solution prefers, not whether one forms. Within 0.2 of either cutoff the published data scatter, so the card adds a borderline note there.", refs: ["guo2011vec"], theory: "sec-vec", eqn: "eq-vec" },
        "Yang–Zhang Ω rule": { sym: "Ω > 1.1", eq: null, inputs: ["melting", "pairs"], interp: "Solid solution favored above 1.1. Unstable near ΔH mix ≈ 0 (reported, not hidden).", refs: ["yang2012"], theory: "sec-omega", eqn: "eq-omega" },
        "King Phi rule": { sym: "Φ > 1", eq: null, inputs: ["pairs", "temperature"], interp: "Solid solution predicted when Φ exceeds 1 at the chosen temperature.", refs: ["king2016"], theory: "sec-prediction", eqn: null },
        "Ye phi rule": { sym: "φ > 20", eq: null, inputs: ["pairs", "melting", "radius"], interp: "Solid solution predicted above 20.", refs: ["ye2015phi"], theory: "sec-prediction", eqn: null },
        "Senkov–Miracle kappa": { sym: "k₁ vs k₁ᶜʳ(T)", eq: "k_1^{\\mathrm{cr}}(T) = 1 + \\dfrac{(1-k_2)\\,T\\,\\Delta S_{\\mathrm{mix}}}{|\\Delta H_{\\mathrm{mix}}|},\\quad k_2 = 0.6", inputs: ["pairs", "temperature"], interp: "Solid solution favored while k₁ = ΔH IM/ΔH mix stays below k₁ᶜʳ(T). The verdict here comes from the direct Gibbs comparison, which stays well defined when ΔH mix ≥ 0, with ΔS IM = 0.6·ΔS mix per the paper and ΔH IM = the most-negative-binary proxy. That pair counts in full however little of its elements the alloy holds, so the card notes when one of them is under 10 at.%.", refs: ["senkov2016"], theory: "sec-kappa", eqn: "eq-kappa" },
        "Tsai sigma window": { sym: "6.88 ≤ VEC ≤ 7.84", eq: null, inputs: ["valence"], interp: "Applies to annealed Cr- and/or V-containing alloys. Inside the window the sigma phase tends to precipitate. Not applicable without Cr or V.", refs: ["tsai2013"], theory: "sec-prediction", eqn: "eq-vec" },
        "Sheikh ductility screen": { sym: "VEC < 4.5", eq: null, inputs: ["valence"], interp: "For single-phase bcc refractory HEAs made only of Ti, Zr, Hf, V, Nb, Ta, Cr, Mo and W: below 4.5 intrinsically ductile, at or above 4.6 brittle. Any other element makes it not applicable. Present it alongside the Guo bands, not as a universal verdict.", refs: ["sheikh2016"], theory: "sec-prediction", eqn: "eq-vec" },
        "Configurational entropy": { sym: "ΔS config", eq: "\\Delta S_{\\mathrm{config}} = -R \\sum_s m_s \\sum_i x_{i,s} \\ln x_{i,s}", inputs: ["shannon"], interp: "Sublattice-weighted ideal mixing entropy per mole of formula units. Ordered sublattices contribute zero.", refs: ["rost2015"], theory: "sec-heo", eqn: "eq-oxide-s" },
        "Entropy per cation site": { sym: "ΔS/site", eq: null, inputs: ["shannon"], interp: "The value the 1.5R rock-salt threshold applies to.", refs: ["rost2015"], theory: "sec-heo", eqn: "eq-oxide-s" },
        "Entropy classification": { sym: "ΔS vs 1.5R", eq: null, inputs: ["shannon"], interp: "Rost's entropy-stabilization regime marker.", refs: ["rost2015"], theory: "sec-heo", eqn: "eq-oxide-s" },
        "Cation size disorder": { sym: "δr", eq: "\\delta_r = 100\\sqrt{\\textstyle\\sum_i x_i (1 - r_i/\\bar r)^2}", inputs: ["shannon"], interp: "Ionic analog of the alloy δ over Shannon radii at the family's coordination.", refs: ["shannon1976", "manchon2025"], theory: "sec-shannon", eqn: "eq-deltar" },
        "A-site size disorder": { sym: "δr(A)", eq: null, inputs: ["shannon"], interp: "Per-sublattice size disorder (A site).", refs: ["shannon1976", "jiang2018"], theory: "sec-perovskite", eqn: "eq-deltar" },
        "B-site size disorder": { sym: "δr(B)", eq: null, inputs: ["shannon"], interp: "Per-sublattice size disorder (B site).", refs: ["shannon1976", "jiang2018"], theory: "sec-perovskite", eqn: "eq-deltar" },
        "Combined size disorder": { sym: "δr*", eq: null, inputs: ["shannon"], interp: "Root sum of squares of the per-sublattice disorders.", refs: ["jiang2018"], theory: "sec-perovskite", eqn: "eq-deltar" },
        "Mean cation radius": { sym: "r̄", eq: null, inputs: ["shannon"], interp: "Composition-weighted mean Shannon radius.", refs: ["shannon1976"], theory: "sec-shannon", eqn: null },
        "Mean A-site radius": { sym: "r̄(A)", eq: null, inputs: ["shannon"], interp: "Mean Shannon radius of the A sublattice.", refs: ["shannon1976"], theory: "sec-perovskite", eqn: null },
        "Mean B-site radius": { sym: "r̄(B)", eq: null, inputs: ["shannon"], interp: "Mean Shannon radius of the B sublattice.", refs: ["shannon1976"], theory: "sec-perovskite", eqn: null },
        "Radius dispersion (sample SD)": { sym: "σ(r)", eq: null, inputs: ["shannon"], interp: "Sample standard deviation of the eight-fold radii, which Spiridigliozzi's fluorite predictor reads directly.", refs: ["spiridigliozzi2021", "spiridigliozzi2023"], theory: "sec-fluorite", eqn: null },
        "Goldschmidt tolerance factor": { sym: "t", eq: "t = \\dfrac{\\bar r_A + r_O}{\\sqrt{2}\\,(\\bar r_B + r_O)}", inputs: ["shannon"], interp: "Cubic perovskites cluster near t = 1 (empirically ~0.9–1.0).", refs: ["goldschmidt1926"], theory: "sec-perovskite", eqn: "eq-tolerance" },
        "Octahedral factor": { sym: "μ", eq: "\\mu = \\bar r_B / r_O", inputs: ["shannon"], interp: "A stable BO₆ octahedron needs 0.414 ≤ μ ≤ 0.732.", refs: ["goldschmidt1926", "manchon2025"], theory: "sec-perovskite", eqn: null },
        "Bartel tolerance factor": { sym: "τ", eq: null, inputs: ["shannon"], interp: "Improved tolerance factor. τ < 4.18 predicts perovskite stability.", refs: ["bartel2019"], theory: "sec-perovskite", eqn: null },
        "Radius ratio": { sym: "r(A)/r(B)", eq: null, inputs: ["shannon"], interp: "Pyrochlores form for 1.46–1.78. Below that range the defect fluorite takes over.", refs: ["subramanian1983"], theory: "sec-fluorite", eqn: null },
        "Mean cation electronegativity": { sym: "χ̄", eq: null, inputs: ["shannon"], interp: "Mean Pauling electronegativity over the cation set.", refs: ["pauling1960"], theory: null, eqn: "eq-chi" },
      };

      const PROV_INPUT_META = {
        radius: { label: "Atomic radius", field: "radius", unit: "pm", pyKey: "radius_pm" },
        melting: { label: "Melting point", field: "melting", unit: "K", pyKey: "melting_K" },
        valence: { label: "VEC", field: "valence", unit: "e/atom", pyKey: "valence" },
        chi: { label: "Pauling χ", field: "chi", unit: "", pyKey: "electronegativity" },
      };

      let provContext = { mode: null, payload: null, report: null };
      let provInvoker = null;

      function provRememberAlloy(payload) {
        provContext = { mode: "alloy", payload: payload, report: null };
      }

      function provRememberOxide(report) {
        provContext = { mode: "oxide", payload: null, report: report };
      }

      function provButtonHtml(title) {
        if (!PROV_REGISTRY[title]) return "";
        return `<button type="button" class="prov-btn" data-prov="${title.replace(/"/g, "&quot;")}" aria-label="Equation, inputs, and sources for ${title.replace(/"/g, "&quot;")}" title="Equation, inputs, and sources">ⓘ</button>`;
      }

      function provSourceLinks(keys) {
        return (keys || []).map((k) => {
          const ref = REFERENCES_JS[k];
          if (!ref) return k;
          return `<a href="#refs" data-jump-view="refs" data-jump-anchor="ref-${k}">${ref.authors.split(",")[0].trim()} ${ref.year}</a>`;
        }).join(" · ");
      }

      function provElementRows(kind) {
        const meta = PROV_INPUT_META[kind];
        const comp = provContext.payload ? provContext.payload.composition : null;
        if (!meta || !comp) return "";
        const srcKeys = (PROPERTY_SOURCES_JS[meta.pyKey] || {}).sourceKeys || [];
        const rows = Object.keys(comp).sort().map((el) => {
          const v = calcCore.ELEMENT_DATA[el] ? calcCore.ELEMENT_DATA[el][meta.field] : null;
          return `<tr><td><a href="#data" data-jump-view="data" data-jump-anchor="data-${el}">${el}</a></td><td>${v === null || v === undefined ? "—" : v}</td><td class="prov-src">${meta.unit}</td></tr>`;
        }).join("");
        return `<table class="prov-inputs"><thead><tr><th>${meta.label}</th><th>value</th><th></th></tr></thead><tbody>${rows}</tbody></table>` +
          `<p class="prov-note">Source: ${provSourceLinks(srcKeys)}. Column conventions are in the <a href="#data" data-jump-view="data">Element data view</a>.</p>`;
      }

      function provPairRows() {
        const comp = provContext.payload ? provContext.payload.composition : null;
        if (!comp) return "";
        const els = Object.keys(comp).sort();
        const rows = [];
        for (let i = 0; i < els.length; i += 1) {
          for (let j = i + 1; j < els.length; j += 1) {
            const key = getPairKey(els[i], els[j]);
            const edited = pairEnthalpyEdits && Object.prototype.hasOwnProperty.call(pairEnthalpyEdits, key);
            const v = edited ? pairEnthalpyEdits[key] : calcCore.PAIR_ENTHALPIES[key];
            rows.push(`<tr${edited ? ' class="prov-edited"' : ""}><td>${key.replace("|", "–")}</td><td>${v === undefined ? "missing" : formatNumber(Number(v), 4)}</td><td class="prov-src">${edited ? "edited by you" : "kJ/mol"}</td></tr>`);
          }
        }
        return `<table class="prov-inputs"><thead><tr><th>Pair ΔH mix</th><th>value</th><th></th></tr></thead><tbody>${rows.join("")}</tbody></table>` +
          `<p class="prov-note">Source: ${provSourceLinks(["deboer1988", "takeuchi2005", "matminer2018"])}. The vendored table is pinned by SHA in the <a href="#data" data-jump-view="data">Element data view</a>.</p>`;
      }

      function provMechanicsRows() {
        const comp = provContext.payload ? provContext.payload.composition : null;
        if (!comp) return "";
        const rows = Object.keys(comp).sort().map((el) => {
          const m = calcCore.ELEMENT_MECHANICS[el];
          return `<tr><td><a href="#data" data-jump-view="data" data-jump-anchor="data-${el}">${el}</a></td><td>${m ? formatNumber(m.B, 4) : "—"}</td><td>${m ? formatNumber(m.Vm, 4) : "—"}</td></tr>`;
        }).join("");
        return `<table class="prov-inputs"><thead><tr><th>El</th><th>B (GPa)</th><th>Vm (cm³/mol)</th></tr></thead><tbody>${rows}</tbody></table>` +
          `<p class="prov-note">Source: ${provSourceLinks(["matminer2018", "deboer1988"])}. The upstream column named “compressibility” holds the bulk modulus in GPa. Details are in the <a href="#data" data-jump-view="data">Element data view</a>.</p>`;
      }

      function provShannonRows() {
        const report = provContext.report;
        if (!report) return "";
        const rows = [];
        Object.keys(report.sites).forEach((siteLabel) => {
          Object.keys(report.sites[siteLabel]).sort().forEach((el) => {
            rows.push(`<tr><td>${el}</td><td>${oxideChargeLabelText(report.oxidation_states[el])}</td><td>${formatNumber(report.shannon_radii[el], 4)}</td><td class="prov-src">${siteLabel} · CN ${report.coordination[siteLabel]}</td></tr>`);
          });
        });
        return `<table class="prov-inputs"><thead><tr><th>Cation</th><th>state</th><th>r (Å)</th><th></th></tr></thead><tbody>${rows.join("")}</tbody></table>` +
          `<p class="prov-note">Shannon (1976) effective ionic radii at the family's coordination. The Theory view gives the assignment rules.</p>`;
      }

      function oxideChargeLabelText(charge) {
        return charge > 0 ? "+" + charge : String(charge);
      }

      function provTemperatureRow() {
        const d = provContext.payload ? provContext.payload.descriptors : null;
        if (!d) return "";
        return `<p class="prov-note">T = ${formatNumber(d.King_temperature_K, 6)} K, from the annealing-temperature input (defaults to the rule-of-mixtures T m).</p>`;
      }

      function provInputsHtml(entry) {
        let html = "";
        (entry.inputs || []).forEach((kind) => {
          if (kind === "composition") {
            html += `<p class="prov-note">Only the normalized mole fractions enter.</p>`;
          } else if (PROV_INPUT_META[kind]) {
            html += provElementRows(kind);
          } else if (kind === "pairs") {
            html += provPairRows();
          } else if (kind === "mechanics") {
            html += provMechanicsRows();
          } else if (kind === "shannon") {
            html += provShannonRows();
          } else if (kind === "temperature") {
            html += provTemperatureRow();
          } else if (kind === "miedema-params") {
            html += `<p class="prov-note">Per-element Miedema parameters (φ*, n<sub>ws</sub>, V<sup>2/3</sup>) from the vendored matminer table. See the <a href="#data" data-jump-view="data">Element data view</a> for the file pin and license.</p>`;
          }
        });
        return html || `<p class="prov-note">Derived from the descriptors above, with no additional element data.</p>`;
      }

      function provRefsHtml(entry) {
        const items = (entry.refs || []).map((k) => {
          const ref = REFERENCES_JS[k];
          if (!ref) return "";
          const link = ref.doi ? `https://doi.org/${ref.doi}` : ref.url;
          return `<li>${ref.authors} (${ref.year}). ${ref.title}. <em>${ref.venue}</em>.` +
            (link ? ` <a href="${link}" target="_blank" rel="noopener noreferrer">${ref.doi ? "doi:" + ref.doi : "link"}</a>` : "") +
            ` · <a href="#refs" data-jump-view="refs" data-jump-anchor="ref-${k}">in bibliography</a></li>`;
        }).join("");
        return `<ul class="prov-refs">${items}</ul>`;
      }

      function escapeHtmlText(text) {
        // TeX riding through innerHTML: "<" (e.g. \sum_{i<j}) must not
        // open an HTML tag, or the math delimiters get eaten before
        // MathJax ever sees them.
        return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      }

      function openProvenance(title, invoker) {
        const entry = PROV_REGISTRY[title];
        const drawer = document.getElementById("prov-drawer");
        if (!entry || !drawer) return;
        provInvoker = invoker || null;
        const card = invoker ? invoker.closest(".result-card") : null;
        const valueText = card ? (card.querySelector("p") ? card.querySelector("p").textContent.trim() : "") : "";
        const unitsText = card ? (card.querySelector(".units") ? card.querySelector(".units").textContent.trim() : "") : "";
        document.getElementById("prov-drawer-title").textContent = title;
        document.getElementById("prov-drawer-symbol").textContent = entry.sym || "";
        const links = [];
        if (entry.theory) links.push(`<a href="#theory" data-jump-view="theory" data-jump-anchor="${entry.theory}">Derivation → Theory</a>`);
        if (entry.eqn) links.push(`<a href="#equations" data-jump-view="reference" data-jump-anchor="${entry.eqn}">Equation reference</a>`);
        links.push(`<a href="#data" data-jump-view="data">Element data view</a>`);
        const body = document.getElementById("prov-drawer-body");
        body.innerHTML =
          (valueText ? `<div class="prov-sec"><h4>Value</h4><div class="prov-value">${valueText}<span class="prov-units">${unitsText}</span></div></div>` : "") +
          (entry.eq ? `<div class="prov-sec"><h4>Equation</h4><div class="prov-eq">\\[${escapeHtmlText(entry.eq)}\\]</div></div>` : "") +
          `<div class="prov-sec"><h4>Inputs used</h4>${provInputsHtml(entry)}</div>` +
          `<div class="prov-sec"><h4>Interpretation</h4><p class="prov-note">${entry.interp || ""}</p></div>` +
          `<div class="prov-sec"><h4>Sources</h4>${provRefsHtml(entry)}` +
          `<div class="prov-actions"><button type="button" id="prov-copy-bibtex">Copy BibTeX</button></div></div>` +
          `<div class="prov-sec"><h4>Cross-links</h4><div class="prov-links">${links.join("")}</div></div>`;
        const copyBtn = document.getElementById("prov-copy-bibtex");
        if (copyBtn) {
          copyBtn.addEventListener("click", () => {
            const bib = (entry.refs || []).map((k) => (REFERENCES_JS[k] ? REFERENCES_JS[k].bibtex : "")).filter(Boolean).join("\n\n");
            navigator.clipboard.writeText(bib).then(() => {
              copyBtn.textContent = "Copied";
              setTimeout(() => { copyBtn.textContent = "Copy BibTeX"; }, 1200);
            }).catch(() => {});
          });
        }
        drawer.hidden = false;
        requestAnimationFrame(() => drawer.classList.add("is-open"));
        if (window.MathJax && typeof window.MathJax.typesetPromise === "function") {
          window.MathJax.typesetPromise([body]).catch(() => {});
        }
        document.getElementById("prov-drawer-close").focus();
      }

      function closeProvenance() {
        const drawer = document.getElementById("prov-drawer");
        if (!drawer || drawer.hidden) return;
        drawer.classList.remove("is-open");
        setTimeout(() => { drawer.hidden = true; }, 240);
        if (provInvoker && document.contains(provInvoker)) provInvoker.focus();
        provInvoker = null;
      }

      document.addEventListener("click", (event) => {
        const btn = event.target.closest(".prov-btn");
        if (btn) {
          event.stopPropagation();
          openProvenance(btn.dataset.prov, btn);
          return;
        }
        const drawer = document.getElementById("prov-drawer");
        if (drawer && !drawer.hidden && !event.target.closest(".prov-drawer")) {
          closeProvenance();
        }
      });
      document.getElementById("prov-drawer-close").addEventListener("click", closeProvenance);
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeProvenance();
      });

      // ---- Cite this result: content-hash ID, permalink, receipt ----
      const PAPER_DOI = "10.3390/ma19143075";
      const CONCEPT_DOI = "10.5281/zenodo.20346287";
      let citeState = null; // { id, permalink, receipt }
      let citeGeneration = 0; // invalidates in-flight result-ID digests

      function canonicalJson(value) {
        if (Array.isArray(value)) {
          return "[" + value.map(canonicalJson).join(",") + "]";
        }
        if (value && typeof value === "object") {
          return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + canonicalJson(value[k])).join(",") + "}";
        }
        if (typeof value === "number" && !isFinite(value)) {
          return JSON.stringify(value > 0 ? "__Infinity__" : "__-Infinity__");
        }
        return JSON.stringify(value);
      }

      function fnv1aHex(text) {
        let h = 0x811c9dc5;
        for (let i = 0; i < text.length; i += 1) {
          h ^= text.charCodeAt(i);
          h = (h * 0x01000193) >>> 0;
        }
        return ("0000000" + h.toString(16)).slice(-8);
      }

      // Two arithmetic routes to one composition (a typed formula and its
      // permalink) can differ in the last bit, which must not change the
      // result ID, so the ID hashes each mole fraction at 12 significant
      // digits. The receipt itself keeps the exact values.
      function idInputs(inputs) {
        if (!inputs || !inputs.composition) return inputs;
        const composition = {};
        Object.keys(inputs.composition).forEach((el) => {
          composition[el] = Number(Number(inputs.composition[el]).toPrecision(12));
        });
        return Object.assign({}, inputs, { composition });
      }

      function resultIdFrom(text) {
        if (window.crypto && window.crypto.subtle && typeof window.crypto.subtle.digest === "function") {
          const bytes = new TextEncoder().encode(text);
          return window.crypto.subtle.digest("SHA-256", bytes).then((buf) => {
            const hex = Array.from(new Uint8Array(buf)).map((b) => ("0" + b.toString(16)).slice(-2)).join("");
            return "hea-" + hex.slice(0, 12);
          }).catch(() => "hea-fnv-" + fnv1aHex(text));
        }
        // No WebCrypto (e.g. plain http): a labeled non-cryptographic fallback.
        return Promise.resolve("hea-fnv-" + fnv1aHex(text));
      }

      function sanitizeForJson(value) {
        if (Array.isArray(value)) return value.map(sanitizeForJson);
        if (value && typeof value === "object") {
          const out = {};
          Object.keys(value).forEach((k) => { out[k] = sanitizeForJson(value[k]); });
          return out;
        }
        if (typeof value === "number" && !isFinite(value)) {
          return value > 0 ? "__Infinity__" : "__-Infinity__";
        }
        return value;
      }

      function buildReceipt(mode) {
        const generated = new Date().toISOString().slice(0, 10);
        const base = {
          schema: "hea-bench-receipt/1",
          app: {
            name: "HEA-Bench",
            version: VERSION,
            surface: "browser",
            paper_doi: PAPER_DOI,
            concept_doi: CONCEPT_DOI,
            cite_note: "Cite the paper for the descriptor definitions and the Zenodo record for the software version.",
          },
          generated: generated,
          data: {
            element_table: "55 elements: radii LA-4003 (1968), melting CRC, VEC Guo convention, chi Pauling set. Per-element notes are in the Data view.",
            pair_table: "Miedema binary enthalpies, de Boer 1988 via Takeuchi-Inoue 2005 and matminer",
            file_sha256: DATA_FILE_SHAS,
            tables_short_sha: DATA_TABLES_SHORT_SHA,
          },
        };
        if (mode === "alloy" && provContext.payload) {
          const overrides = Object.keys(pairEnthalpyEdits || {}).length ? pairEnthalpyEdits : null;
          base.inputs = {
            mode: "alloy",
            composition: provContext.payload.composition,
            annealing_temperature_K: provContext.payload.descriptors.King_temperature_K,
            pair_enthalpy_overrides_kj_mol: overrides,
          };
          base.outputs = {
            descriptors: sanitizeForJson(provContext.payload.descriptors),
            rules: sanitizeForJson(provContext.payload.rules),
            warnings: provContext.payload.warnings || [],
          };
        } else if (mode === "oxide" && provContext.report) {
          base.inputs = {
            mode: "oxide",
            family: provContext.report.family,
            sites: provContext.report.sites,
          };
          base.outputs = sanitizeForJson(provContext.report);
        }
        base.references = Object.keys(REFERENCES_JS).sort().map((k) => ({
          key: k,
          doi: REFERENCES_JS[k].doi || null,
          url: REFERENCES_JS[k].url || null,
        }));
        return base;
      }

      function renderCitePanel(mode) {
        const panel = document.getElementById("cite-panel");
        if (!panel) return;
        if (!mode) {
          panel.classList.add("hidden");
          citeState = null;
          return;
        }
        const receipt = buildReceipt(mode);
        if (!receipt.inputs) {
          panel.classList.add("hidden");
          citeState = null;
          return;
        }
        const permalink = mode === "alloy" ? buildShareUrl() : null;
        const idPayload = canonicalJson({ v: VERSION, inputs: idInputs(receipt.inputs) });
        document.getElementById("cite-version").textContent = "v" + VERSION + " · data " + DATA_TABLES_SHORT_SHA;
        const permRow = document.getElementById("cite-permalink-row");
        if (permalink) {
          permRow.style.display = "";
          document.getElementById("cite-permalink").textContent = permalink;
        } else {
          permRow.style.display = "none";
        }
        document.getElementById("cite-result-id").textContent = "computing…";
        citeState = null; // stale state must not be copyable while the new ID computes
        citeGeneration += 1;
        const generation = citeGeneration;
        resultIdFrom(idPayload).then((id) => {
          if (generation !== citeGeneration) return; // a newer calculation superseded this one
          receipt.result_id = id;
          if (permalink) receipt.permalink = permalink;
          citeState = { id: id, permalink: permalink, receipt: receipt, mode: mode };
          document.getElementById("cite-result-id").textContent = id;
        });
        panel.classList.remove("hidden");
      }

      function citeMessage(text) {
        const el = document.getElementById("cite-message");
        el.textContent = text;
        setTimeout(() => { if (el.textContent === text) el.textContent = ""; }, 2000);
      }

      function citationText() {
        if (!citeState) return "";
        const today = new Date().toISOString().slice(0, 10);
        return "HEA-Bench v" + VERSION + " (browser app), result " + citeState.id +
          (citeState.permalink ? ", " + citeState.permalink : "") +
          ", retrieved " + today + ". Software archive: doi:" + CONCEPT_DOI +
          ". Descriptor definitions: Fieser, Dewanjee & Hu (2026), Materials 19, 3075, doi:" + PAPER_DOI + ".";
      }

      function citationBibtex() {
        if (!citeState) return "";
        const today = new Date().toISOString().slice(0, 10);
        const softwareEntry = "@software{heabench_v" + VERSION.replace(/\./g, "_") + ",\n" +
          "  author = {Fieser, David and Dewanjee, Unmanaa and Hu, Anming},\n" +
          "  title = {HEA-Bench (browser app)},\n" +
          "  version = {" + VERSION + "},\n" +
          "  doi = {" + CONCEPT_DOI + "},\n" +
          (citeState.permalink ? "  url = {" + citeState.permalink + "},\n" : "") +
          "  note = {Result " + citeState.id + ", retrieved " + today + "},\n" +
          "  year = {2026},\n}";
        const paperEntry = REFERENCES_JS.heabench2026 ? REFERENCES_JS.heabench2026.bibtex : "";
        return softwareEntry + "\n\n" + paperEntry;
      }

      function bindCitePanel() {
        const copyText = document.getElementById("cite-copy-text");
        const copyBib = document.getElementById("cite-copy-bibtex");
        const copyReceipt = document.getElementById("cite-copy-receipt");
        const download = document.getElementById("cite-download-receipt");
        if (!copyText) return;
        const notReady = () => { citeMessage("Result ID is still computing. Try again in a moment."); };
        copyText.addEventListener("click", () => {
          if (!citeState) { notReady(); return; }
          navigator.clipboard.writeText(citationText()).then(() => citeMessage("Citation copied.")).catch(() => citeMessage("Clipboard unavailable."));
        });
        copyBib.addEventListener("click", () => {
          if (!citeState) { notReady(); return; }
          navigator.clipboard.writeText(citationBibtex()).then(() => citeMessage("BibTeX copied.")).catch(() => citeMessage("Clipboard unavailable."));
        });
        copyReceipt.addEventListener("click", () => {
          if (!citeState) { notReady(); return; }
          navigator.clipboard.writeText(JSON.stringify(citeState.receipt, null, 2)).then(() => citeMessage("Receipt copied.")).catch(() => citeMessage("Clipboard unavailable."));
        });
        download.addEventListener("click", () => {
          if (!citeState) { notReady(); return; }
          const blob = new Blob([JSON.stringify(citeState.receipt, null, 2)], { type: "application/json" });
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = "hea-bench-receipt-" + citeState.id + ".json";
          document.body.appendChild(a);
          a.click();
          setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 400);
          citeMessage("Receipt downloaded.");
        });
      }
      bindCitePanel();

      // ---- Data view: the source-data browser -----------------------
      let dataSortKey = "symbol";
      let dataSortAsc = true;

      function dataElementRows() {
        const els = Object.keys(calcCore.ELEMENT_DATA);
        const rows = els.map((el) => {
          const d = calcCore.ELEMENT_DATA[el];
          return { symbol: el, radius: d.radius, melting: d.melting, valence: d.valence, chi: d.chi };
        });
        rows.sort((a, b) => {
          const va = a[dataSortKey];
          const vb = b[dataSortKey];
          const cmp = typeof va === "string" ? va.localeCompare(vb) : va - vb;
          return dataSortAsc ? cmp : -cmp;
        });
        return rows;
      }

      function dataNoteHtml(el) {
        const src = ELEMENT_SOURCES_JS[el] || {};
        const parts = [];
        const srcRef = REFERENCES_JS[src.radiusSource];
        if (srcRef) {
          parts.push(`Radius source: <a href="#refs" data-jump-view="refs" data-jump-anchor="ref-${src.radiusSource}">${srcRef.authors.split(",")[0].trim()} ${srcRef.year}</a>.`);
        }
        if (src.crosscheckRadiusPm !== null && src.crosscheckRadiusPm !== undefined) {
          const ours = calcCore.ELEMENT_DATA[el].radius;
          const diff = Math.abs(ours - src.crosscheckRadiusPm);
          const agree = diff <= 1.0;
          parts.push(
            `Cross-check radius (M&amp;S 2017 Table 3): <span class="${agree ? "" : "data-el-crossdiff"}">${src.crosscheckRadiusPm} pm</span>` +
            (agree ? `. Agrees within ${diff.toFixed(1)} pm.` : `. Differs by ${diff.toFixed(1)} pm. ${src.crosscheckNote || "See note."}`)
          );
        } else if (src.crosscheckNote) {
          parts.push(src.crosscheckNote);
        }
        if (src.notes) parts.push(src.notes);
        const flags = (src.flags || []).map((f) => `<span class="data-el-flag">${f}</span>`).join("");
        return parts.join(" ") + (flags ? `<div>${flags}</div>` : "");
      }

      function renderDataElementTable() {
        const tbody = document.getElementById("data-element-tbody");
        if (!tbody) return;
        const filter = (document.getElementById("data-filter").value || "").trim().toLowerCase();
        const rows = dataElementRows().filter((r) => !filter || r.symbol.toLowerCase().indexOf(filter) === 0);
        tbody.innerHTML = rows.map((r) => {
          const hasNote = ELEMENT_SOURCES_JS[r.symbol] && (
            ELEMENT_SOURCES_JS[r.symbol].notes ||
            ELEMENT_SOURCES_JS[r.symbol].crosscheckRadiusPm !== null ||
            (ELEMENT_SOURCES_JS[r.symbol].flags || []).length
          );
          return `<tr id="data-${r.symbol}">` +
            `<td>${r.symbol}</td><td>${r.radius}</td><td>${r.melting}</td><td>${r.valence}</td><td>${r.chi}</td>` +
            `<td>${hasNote ? `<button type="button" class="data-toggle" data-el="${r.symbol}" aria-expanded="false">sources &amp; flags</button>` : `<span class="small-note">standard set</span>`}</td>` +
            `</tr>`;
        }).join("");
        document.getElementById("data-count").textContent = rows.length + " of " + Object.keys(calcCore.ELEMENT_DATA).length + " elements";
      }

      function buildDataView() {
        if (!document.getElementById("data-element-tbody")) return;
        const colsrc = document.getElementById("data-colsrc");
        colsrc.innerHTML = ["radius_pm", "melting_K", "valence", "electronegativity"].map((k) => {
          const ps = PROPERTY_SOURCES_JS[k];
          if (!ps) return "";
          return `<strong>${k}</strong>: ${ps.statement} [${provSourceLinks(ps.sourceKeys)}]`;
        }).join("<br>");
        renderDataElementTable();

        document.getElementById("data-filter").addEventListener("input", renderDataElementTable);
        document.querySelectorAll("#data-element-table th[data-sort]").forEach((th) => {
          th.addEventListener("click", () => {
            const key = th.dataset.sort;
            if (dataSortKey === key) { dataSortAsc = !dataSortAsc; } else { dataSortKey = key; dataSortAsc = true; }
            renderDataElementTable();
          });
        });
        document.getElementById("data-element-tbody").addEventListener("click", (event) => {
          const btn = event.target.closest(".data-toggle");
          if (!btn) return;
          const tr = btn.closest("tr");
          const open = btn.getAttribute("aria-expanded") === "true";
          if (open) {
            const next = tr.nextElementSibling;
            if (next && next.classList.contains("data-el-note-row")) next.remove();
            btn.setAttribute("aria-expanded", "false");
          } else {
            const note = document.createElement("tr");
            note.className = "data-el-note-row";
            note.innerHTML = `<td colspan="6">${dataNoteHtml(btn.dataset.el)}</td>`;
            tr.after(note);
            btn.setAttribute("aria-expanded", "true");
          }
        });

        const selA = document.getElementById("data-pair-a");
        const selB = document.getElementById("data-pair-b");
        const out = document.getElementById("data-pair-value");
        const opts = Object.keys(calcCore.ELEMENT_DATA).map((el) => `<option value="${el}">${el}</option>`).join("");
        selA.innerHTML = opts;
        selB.innerHTML = opts;
        selB.selectedIndex = 1;
        function updatePair() {
          const a = selA.value;
          const b = selB.value;
          if (a === b) { out.textContent = "pick two different elements"; return; }
          const v = calcCore.PAIR_ENTHALPIES[getPairKey(a, b)];
          out.textContent = v === undefined
            ? `${a}–${b}: not in the vendored table (the documented Th–U gap)`
            : `ΔH mix(${a}–${b}) = ${v} kJ/mol · de Boer 1988 via matminer`;
        }
        selA.addEventListener("change", updatePair);
        selB.addEventListener("change", updatePair);
        updatePair();

        const files = [
          { name: "elemental.py", desc: "The 55-element property table (radii, melting points, VEC, chi) with per-element source comments.", up: "https://github.com/dfieser/hea-bench/blob/main/src/hea_bench/descriptors/data/elemental.py", license: "MIT (hea-bench)" },
          { name: "pair_enthalpies.tsv", desc: "2628 Miedema binary mixing enthalpies over 75 elements, vendored from matminer's MiedemaLiquidDeltaHf.tsv.", up: "https://github.com/hackingmaterials/matminer/blob/main/src/matminer/utils/data_files/MiedemaLiquidDeltaHf.tsv", license: "BSD-3-Clause (matminer)" },
          { name: "miedema_parameters.csv", desc: "Per-element Miedema parameters and mechanics (molar volume, and the bulk modulus in GPa under the upstream column named 'compressibility').", up: "https://github.com/hackingmaterials/matminer/blob/main/src/matminer/utils/data_files/Miedema.csv", license: "BSD-3-Clause (matminer)" },
          { name: "provenance.py", desc: "The per-element source notes, cross-check values, and bibliography this page renders.", up: "https://github.com/dfieser/hea-bench/blob/main/src/hea_bench/descriptors/data/provenance.py", license: "MIT (hea-bench)" },
        ];
        document.getElementById("data-files-list").innerHTML = files.map((f) => {
          const sha = DATA_FILE_SHAS[f.name] || "";
          return `<div class="data-file-card"><span class="data-file-name">${f.name}</span>: ${f.desc}<br>` +
            `<code>sha256 ${sha}</code><br>` +
            `<a href="${f.up}" target="_blank" rel="noopener noreferrer">upstream</a> · ${f.license}</div>`;
        }).join("") + `<p class="small-note">Combined data fingerprint: <code>${DATA_TABLES_SHORT_SHA}</code>. It appears in the footer badge and in every receipt.</p>`;

        const covBody = document.getElementById("data-coverage-tbody");
        covBody.innerHTML = Object.keys(calcCore.ELEMENT_DATA).map((el) => {
          const mech = calcCore.ELEMENT_MECHANICS[el];
          const mied = Boolean(calcCore.MIEDEMA_TABLE[el]);
          return `<tr><td>${el}</td><td>✓</td><td>${mech && mech.B > 0 && mech.Vm > 0 ? "✓" : "✗"}</td><td>${mied ? "✓" : "✗"}</td></tr>`;
        }).join("");
      }
      buildDataView();

      // Click-to-copy on every numeric result card.
      [
        resultsEl,
        miedemaResultsEl,
        document.getElementById("rule-predictions"),
        oxideResultsEl,
        oxideVerdictsEl,
      ].forEach((container) => {
        if (!container) return;
        container.addEventListener("click", (event) => {
          if (event.target.closest(".prov-btn")) return;
          const card = event.target.closest(".result-card");
          if (!card || card.classList.contains("composition-card")) return;
          const valueEl = card.querySelector("p");
          if (!valueEl) return;
          const text = valueEl.textContent.trim();
          if (!text || text === "—") return;
          navigator.clipboard.writeText(text).then(() => {
            card.classList.add("copied");
            setTimeout(() => card.classList.remove("copied"), 900);
          }).catch(() => { /* clipboard unavailable */ });
        });
      });

      // Ctrl+Enter (or Cmd+Enter) calculates in whichever mode is active.
      document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
          if (document.body.classList.contains("mode-oxide")) {
            handleOxideCalculate();
          } else if (document.body.classList.contains("mode-ceramic")) {
            document.getElementById("ceramic-calculate").click();
          } else {
            handleCalculate();
          }
        }
      });

      // Manual theme override (auto follows the OS preference).
      const THEME_STORAGE_KEY = "hea-bench-theme";
      const themeToggleBtn = document.getElementById("theme-toggle");
      const THEME_SEQUENCE = ["auto", "light", "dark"];
      const THEME_ICONS = { auto: "◐", light: "○", dark: "●" };
      let currentTheme = "auto";

      function applyTheme(theme) {
        currentTheme = theme;
        if (theme === "auto") {
          document.documentElement.removeAttribute("data-theme");
        } else {
          document.documentElement.setAttribute("data-theme", theme);
        }
        themeToggleBtn.textContent = THEME_ICONS[theme];
        themeToggleBtn.title = "Theme: " + theme + " (click to change)";
        try { localStorage.setItem(THEME_STORAGE_KEY, theme); } catch (e) { /* storage unavailable */ }
      }

      themeToggleBtn.addEventListener("click", () => {
        const next = THEME_SEQUENCE[(THEME_SEQUENCE.indexOf(currentTheme) + 1) % THEME_SEQUENCE.length];
        applyTheme(next);
      });
      let storedTheme = "auto";
      try { storedTheme = localStorage.getItem(THEME_STORAGE_KEY) || "auto"; } catch (e) { /* storage unavailable */ }
      if (storedTheme !== "auto") applyTheme(storedTheme);

      // What's-new popover on the version badge.
      const aboutPopoverEl = document.getElementById("about-popover");
      const aboutHistoryEl = document.getElementById("about-history");
      const versionBadgeEl = document.getElementById("version-badge");

      function buildAboutHistory() {
        aboutHistoryEl.innerHTML = "";
        VERSION_HISTORY.forEach((entry) => {
          const div = document.createElement("div");
          div.className = "about-entry";
          div.innerHTML =
            `<span class="about-version">v${entry.version}</span>` +
            `<span class="about-date">${entry.date}</span>` +
            `<p class="about-notes">${entry.notes}</p>`;
          aboutHistoryEl.appendChild(div);
        });
      }

      versionBadgeEl.addEventListener("click", (event) => {
        event.stopPropagation();
        if (aboutPopoverEl.classList.contains("hidden")) buildAboutHistory();
        aboutPopoverEl.classList.toggle("hidden");
      });
      document.addEventListener("click", (event) => {
        if (!aboutPopoverEl.classList.contains("hidden") &&
            !aboutPopoverEl.contains(event.target)) {
          aboutPopoverEl.classList.add("hidden");
        }
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") aboutPopoverEl.classList.add("hidden");
      });

      // Welcome quick-start actions.
      const emptyLoadOxideBtn = document.getElementById("empty-load-oxide");
      if (emptyLoadOxideBtn) {
        emptyLoadOxideBtn.addEventListener("click", () => {
          applyMode("oxide");
          oxideExampleEl.value = "j14";
          oxideExampleEl.dispatchEvent(new Event("change"));
        });
      }
      const emptyOpenTheoryBtn = document.getElementById("empty-open-theory");
      if (emptyOpenTheoryBtn) {
        emptyOpenTheoryBtn.addEventListener("click", () => {
          const theoryTab = document.querySelector('.titlebar__tabs .tab[data-view="theory"]');
          if (theoryTab) theoryTab.click();
        });
      }
      const oxideEmptyExampleBtn = document.getElementById("oxide-empty-example");
      if (oxideEmptyExampleBtn) {
        oxideEmptyExampleBtn.addEventListener("click", () => {
          oxideExampleEl.value = "j14";
          oxideExampleEl.dispatchEvent(new Event("change"));
        });
      }

      customSaveBtn.addEventListener("click", () => {
        showError("");
        showCustomMessage("");

        const label = String(customLabelInput.value || "").trim();
        const radius = Number(customRadiusInput.value);
        const melting = Number(customMeltingInput.value);
        const valence = Number(customValenceInput.value);
        const chiRaw = String(customChiInput.value || "").trim();
        const chi = chiRaw === "" ? NaN : Number(chiRaw);

        if (!isValidCustomLabel(label)) {
          showCustomMessage("Label must be unique (not built-in) and 1–10 characters (letters/numbers/_/-). ");
          return;
        }
        if (!Number.isFinite(radius) || radius <= 0) {
          showCustomMessage("Enter a valid atomic radius (> 0).");
          return;
        }
        if (!Number.isFinite(melting) || melting <= 0) {
          showCustomMessage("Enter a valid melting temperature (> 0).");
          return;
        }
        if (!Number.isFinite(valence) || valence < 0) {
          showCustomMessage("Enter a valid valence electron count (≥ 0).");
          return;
        }
        if (chiRaw !== "" && (!Number.isFinite(chi) || chi <= 0)) {
          showCustomMessage("Electronegativity must be a positive number (or leave it blank).");
          return;
        }

        const original = customEditOriginalLabel;
        const nameConflict = customElements.some((e) => e.label === label && e.label !== original);
        if (nameConflict) {
          showCustomMessage("That custom label already exists.");
          return;
        }

        if (original && original !== label) {
          removeCustomFromData(original);
        }

        const nextRecord = Number.isFinite(chi)
          ? { label, radius, melting, valence, chi }
          : { label, radius, melting, valence };
        if (original) {
          customElements = customElements.map((e) => (e.label === original ? nextRecord : e));
        } else {
          customElements = [...customElements, nextRecord];
        }
        customElements.sort((a, b) => a.label.localeCompare(b.label));
        saveCustomElements(customElements);
        applyCustomElementsToData([nextRecord]);

        const snapshot = snapshotCompositionTable();
        renderRatioTable(Number(elementCountInput.value) || 5);
        if (snapshot) {
          if (original && original !== label) {
            snapshot.elements = snapshot.elements.map((v) => (v === original ? label : v));
          }
          restoreCompositionTable(snapshot);
        }
        if (customTriggeredSelectIndex !== null) {
          const select = ratioTableEl.querySelector(`select[data-element-index="${customTriggeredSelectIndex}"]`);
          if (select) select.value = label;
        }

        if (original && original !== label) {
          remapPairEnthalpyEdits(original, label);
        }

        renderPairEnthalpyEditor();
        renderCustomElementsSection();
        showCustomMessage("Saved.");
        closeCustomPanel();
        scheduleSaveFormState();
      });

      customCancelBtn.addEventListener("click", () => {
        closeCustomPanel();
      });

      customRemoveBtn.addEventListener("click", () => {
        if (!customEditOriginalLabel) {
          closeCustomPanel();
          return;
        }
        deleteCustomElementByLabel(customEditOriginalLabel);
        closeCustomPanel();
        scheduleSaveFormState();
      });

      customElementsBodyEl.addEventListener("click", (event) => {
        const target = event.target;
        if (!target || !target.getAttribute) return;
        const editLabel = target.getAttribute("data-custom-edit");
        const deleteLabel = target.getAttribute("data-custom-delete");
        if (editLabel) {
          openCustomPanel(null, editLabel);
          return;
        }
        if (deleteLabel) {
          deleteCustomElementByLabel(deleteLabel);
        }
      });

      pairEnthalpyEditorEl.addEventListener("input", (event) => {
        const target = event.target;
        if (!target || !target.matches || !target.matches("input[data-pair-key]")) return;
        const key = target.getAttribute("data-pair-key");
        const raw = target.value;
        if (!raw.trim()) {
          delete pairEnthalpyEdits[key];
          scheduleSaveFormState();
          return;
        }
        const num = Number(raw);
        if (!Number.isFinite(num)) return;
        pairEnthalpyEdits[key] = num;
        scheduleSaveFormState();
      });

      saveResultBtn.addEventListener("click", () => {
        showError("");
        saveCurrentResult();
      });
      downloadCsvBtn.addEventListener("click", downloadCsv);
      savedResultsBodyEl.addEventListener("click", (event) => {
        const target = event.target;
        if (!target || !target.getAttribute) return;
        const id = target.getAttribute("data-delete-row");
        if (!id) return;
        deleteSavedRow(id);
      });

      customElements = loadCustomElements();
      applyCustomElementsToData(customElements);

      renderCustomElementsSection();

      savedResults = loadSavedResults();

      const urlApplied = applyUrlParams();
      if (urlApplied !== true) {
        // No permalink result to show: restore the last inputs (or the
        // defaults) and show the empty state until Calculate, so every
        // number on screen comes from the inputs shown next to it.
        if (!applyFormState(loadFormState())) {
          renderRatioTable(5);
          renderPairEnthalpyEditor();
        }
        renderResults(null);
        renderWarnings([]);
      }
      renderSavedResultsTable();

      document.getElementById("version-badge").textContent = "v" + VERSION + " · " + VERSION_DATE + " · data " + DATA_TABLES_SHORT_SHA;
      document.getElementById("landing-version").textContent = "hea-bench " + VERSION + ", released " + VERSION_DATE + ". ";
