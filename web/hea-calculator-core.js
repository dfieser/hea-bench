(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.HeaCalculatorCore = api;
  }
})(
  typeof globalThis !== "undefined" ? globalThis : (typeof self !== "undefined" ? self : this),
  function () {
    "use strict";

    var R = 8.314;
    var KING_PHI_THRESHOLD = 1.0;
    var YE_PHI_THRESHOLD = 20.0;
    var PACKING_FRACTION_BCC = 0.68;
    var PACKING_FRACTION_FCC = 0.74;
    var YEH_HEA_FACTOR = 1.5;
    var ZHANG_DELTA_THRESHOLD = 6.5;
    var YANG_OMEGA_THRESHOLD = 1.1;
    var GUO_VEC_FCC_THRESHOLD = 8.0;
    var GUO_VEC_BCC_THRESHOLD = 6.87;

    var DEFAULT_ELEMENT_DATA = {
      Ag: { radius: 144.0, melting: 1234.93, valence: 11 },
      Al: { radius: 143.0, melting: 933.47, valence: 3 },
      Co: { radius: 125.0, melting: 1768.0, valence: 9 },
      Cr: { radius: 129.0, melting: 2180.0, valence: 6 },
      Cu: { radius: 128.0, melting: 1357.77, valence: 11 },
      Fe: { radius: 126.0, melting: 1811.0, valence: 8 },
      Hf: { radius: 159.0, melting: 2506.0, valence: 4 },
      Ir: { radius: 136.0, melting: 2719.0, valence: 9 },
      Mn: { radius: 135.7, melting: 1519.0, valence: 7 },
      Mo: { radius: 139.0, melting: 2896.0, valence: 6 },
      Nb: { radius: 147.0, melting: 2750.0, valence: 5 },
      Ni: { radius: 125.0, melting: 1728.0, valence: 10 },
      Os: { radius: 135.0, melting: 3306.0, valence: 8 },
      Pd: { radius: 137.0, melting: 1828.0, valence: 10 },
      Pt: { radius: 139.0, melting: 2041.4, valence: 10 },
      Rh: { radius: 134.0, melting: 2237.0, valence: 9 },
      Ru: { radius: 134.0, melting: 2607.0, valence: 8 },
      Si: { radius: 111.0, melting: 1687.0, valence: 4 },
      Ta: { radius: 147.0, melting: 3290.0, valence: 5 },
      Ti: { radius: 147.0, melting: 1941.0, valence: 4 },
      V: { radius: 135.0, melting: 2183.0, valence: 5 },
      W: { radius: 141.0, melting: 3695.0, valence: 6 },
      Y: { radius: 182.0, melting: 1799.0, valence: 3 },
      Zr: { radius: 160.0, melting: 2128.0, valence: 4 }
    };

    var BROWSER_MIEDEMA_PARAMS = {
      Ag: { phi_star: 4.35, nws13: 1.36, V23: 4.72, cls: "TM" },
      Al: { phi_star: 4.20, nws13: 1.39, V23: 4.64, cls: "NTM" },
      Co: { phi_star: 5.10, nws13: 1.75, V23: 3.55, cls: "TM" },
      Cr: { phi_star: 4.65, nws13: 1.73, V23: 3.74, cls: "TM" },
      Cu: { phi_star: 4.45, nws13: 1.47, V23: 3.70, cls: "TM" },
      Fe: { phi_star: 4.93, nws13: 1.77, V23: 3.69, cls: "TM" },
      Hf: { phi_star: 3.60, nws13: 1.45, V23: 5.65, cls: "TM" },
      Ir: { phi_star: 5.55, nws13: 1.83, V23: 4.17, cls: "TM" },
      Mn: { phi_star: 4.45, nws13: 1.61, V23: 3.78, cls: "TM" },
      Mo: { phi_star: 4.65, nws13: 1.77, V23: 4.45, cls: "TM" },
      Nb: { phi_star: 4.05, nws13: 1.64, V23: 4.89, cls: "TM" },
      Ni: { phi_star: 5.20, nws13: 1.75, V23: 3.52, cls: "TM" },
      Os: { phi_star: 5.40, nws13: 1.85, V23: 4.15, cls: "TM" },
      Pd: { phi_star: 5.45, nws13: 1.67, V23: 4.29, cls: "TM" },
      Pt: { phi_star: 5.65, nws13: 1.78, V23: 4.36, cls: "TM" },
      Rh: { phi_star: 5.40, nws13: 1.76, V23: 4.10, cls: "TM" },
      Ru: { phi_star: 5.40, nws13: 1.83, V23: 4.60, cls: "TM" },
      Si: { phi_star: 4.70, nws13: 1.50, V23: 4.20, cls: "NTM" },
      Ta: { phi_star: 4.05, nws13: 1.63, V23: 4.89, cls: "TM" },
      Ti: { phi_star: 3.80, nws13: 1.52, V23: 4.12, cls: "TM" },
      V: { phi_star: 4.25, nws13: 1.64, V23: 4.12, cls: "TM" },
      W: { phi_star: 4.80, nws13: 1.81, V23: 4.50, cls: "TM" },
      Y: { phi_star: 3.20, nws13: 1.21, V23: 7.34, cls: "TM" },
      Zr: { phi_star: 3.45, nws13: 1.41, V23: 5.81, cls: "TM" }
    };

    var BROWSER_MIEDEMA_PAIR_P = { "TM-TM": 14.2, "TM-NTM": 12.35, "NTM-NTM": 10.7 };
    var BROWSER_MIEDEMA_QP_RATIO = 9.4;
    var BROWSER_MIEDEMA_R_OVER_P = { Al: 1.9, Si: 2.1 };
    var BROWSER_MIEDEMA_A_VOL = {
      Ag: 0.07,
      Al: 0.07,
      Co: 0.04,
      Cr: 0.04,
      Cu: 0.07,
      Fe: 0.04,
      Hf: 0.04,
      Ir: 0.04,
      Mn: 0.04,
      Mo: 0.04,
      Nb: 0.04,
      Ni: 0.04,
      Os: 0.04,
      Pd: 0.04,
      Pt: 0.04,
      Rh: 0.04,
      Ru: 0.04,
      Si: 0.04,
      Ta: 0.04,
      Ti: 0.04,
      V: 0.04,
      W: 0.04,
      Y: 0.04,
      Zr: 0.04
    };

    var PAIR_ENTHALPIES = {
      "Ag|Al": -4.0,
      "Ag|Co": 19.0,
      "Ag|Cr": 27.0,
      "Ag|Cu": 2.0,
      "Ag|Fe": 28.0,
      "Ag|Hf": -13.0,
      "Ag|Ir": 16.0,
      "Ag|Mn": 13.0,
      "Ag|Mo": 37.0,
      "Ag|Nb": 16.0,
      "Ag|Ni": 15.0,
      "Ag|Os": 28.0,
      "Ag|Pd": -7.0,
      "Ag|Pt": -1.0,
      "Ag|Rh": 10.0,
      "Ag|Ru": 23.0,
      "Ag|Si": -20.0,
      "Ag|Ta": 15.0,
      "Ag|Ti": -2.0,
      "Ag|V": 17.0,
      "Ag|W": 43.0,
      "Ag|Y": -29.0,
      "Ag|Zr": -20.0,
      "Al|Co": -19.0,
      "Al|Cr": -10.0,
      "Al|Cu": -1.0,
      "Al|Fe": -11.0,
      "Al|Hf": -39.0,
      "Al|Ir": -30.0,
      "Al|Mn": -19.0,
      "Al|Mo": -5.0,
      "Al|Nb": -18.0,
      "Al|Ni": -22.0,
      "Al|Os": -18.0,
      "Al|Pd": -46.0,
      "Al|Pt": -44.0,
      "Al|Rh": -32.0,
      "Al|Ru": -21.0,
      "Al|Si": -19.0,
      "Al|Ta": -19.0,
      "Al|Ti": -30.0,
      "Al|V": -16.0,
      "Al|W": -2.0,
      "Al|Y": -38.0,
      "Al|Zr": -44.0,
      "Co|Cr": -4.0,
      "Co|Cu": 6.0,
      "Co|Fe": -1.0,
      "Co|Hf": -35.0,
      "Co|Ir": -3.0,
      "Co|Mn": -5.0,
      "Co|Mo": -5.0,
      "Co|Nb": -25.0,
      "Co|Ni": 0.0,
      "Co|Os": 0.0,
      "Co|Pd": -1.0,
      "Co|Pt": -7.0,
      "Co|Rh": -2.0,
      "Co|Ru": -1.0,
      "Co|Si": -38.0,
      "Co|Ta": -24.0,
      "Co|Ti": -28.0,
      "Co|V": -14.0,
      "Co|W": -1.0,
      "Co|Y": -22.0,
      "Co|Zr": -41.0,
      "Cr|Cu": 12.0,
      "Cr|Fe": -1.0,
      "Cr|Hf": -9.0,
      "Cr|Ir": -18.0,
      "Cr|Mn": 2.0,
      "Cr|Mo": 0.0,
      "Cr|Nb": -7.0,
      "Cr|Ni": -7.0,
      "Cr|Os": -11.0,
      "Cr|Pd": -15.0,
      "Cr|Pt": -24.0,
      "Cr|Rh": -13.0,
      "Cr|Ru": -12.0,
      "Cr|Si": -37.0,
      "Cr|Ta": -7.0,
      "Cr|Ti": -7.0,
      "Cr|V": -2.0,
      "Cr|W": 1.0,
      "Cr|Y": 11.0,
      "Cr|Zr": -12.0,
      "Cu|Fe": 13.0,
      "Cu|Hf": -17.0,
      "Cu|Ir": 0.0,
      "Cu|Mn": 4.0,
      "Cu|Mo": 19.0,
      "Cu|Nb": 3.0,
      "Cu|Ni": 4.0,
      "Cu|Os": 10.0,
      "Cu|Pd": -14.0,
      "Cu|Pt": -12.0,
      "Cu|Rh": -2.0,
      "Cu|Ru": 7.0,
      "Cu|Si": -19.0,
      "Cu|Ta": 2.0,
      "Cu|Ti": -9.0,
      "Cu|V": 5.0,
      "Cu|W": 22.0,
      "Cu|Y": -22.0,
      "Cu|Zr": -23.0,
      "Fe|Hf": -21.0,
      "Fe|Ir": -9.0,
      "Fe|Mn": 0.0,
      "Fe|Mo": -2.0,
      "Fe|Nb": -16.0,
      "Fe|Ni": -2.0,
      "Fe|Os": -4.0,
      "Fe|Pd": -4.0,
      "Fe|Pt": -13.0,
      "Fe|Rh": -5.0,
      "Fe|Ru": -5.0,
      "Fe|Si": -35.0,
      "Fe|Ta": -15.0,
      "Fe|Ti": -17.0,
      "Fe|V": -7.0,
      "Fe|W": 0.0,
      "Fe|Y": -1.0,
      "Fe|Zr": -25.0,
      "Hf|Ir": -68.0,
      "Hf|Mn": -12.0,
      "Hf|Mo": -4.0,
      "Hf|Nb": 4.0,
      "Hf|Ni": -42.0,
      "Hf|Os": -48.0,
      "Hf|Pd": -80.0,
      "Hf|Pt": -90.0,
      "Hf|Rh": -63.0,
      "Hf|Ru": -52.0,
      "Hf|Si": -77.0,
      "Hf|Ta": 3.0,
      "Hf|Ti": 0.0,
      "Hf|V": -2.0,
      "Hf|W": -6.0,
      "Hf|Y": 11.0,
      "Hf|Zr": 0.0,
      "Ir|Mn": -18.0,
      "Ir|Mo": -21.0,
      "Ir|Nb": -53.0,
      "Ir|Ni": -2.0,
      "Ir|Os": -1.0,
      "Ir|Pd": 6.0,
      "Ir|Pt": 0.0,
      "Ir|Rh": 1.0,
      "Ir|Ru": -1.0,
      "Ir|Si": -43.0,
      "Ir|Ta": -52.0,
      "Ir|Ti": -57.0,
      "Ir|V": -34.0,
      "Ir|W": -16.0,
      "Ir|Y": -53.0,
      "Ir|Zr": -76.0,
      "Mn|Mo": 5.0,
      "Mn|Nb": -4.0,
      "Mn|Ni": -8.0,
      "Mn|Os": -9.0,
      "Mn|Pd": -23.0,
      "Mn|Pt": -28.0,
      "Mn|Rh": -16.0,
      "Mn|Ru": -11.0,
      "Mn|Si": -45.0,
      "Mn|Ta": -4.0,
      "Mn|Ti": -8.0,
      "Mn|V": -1.0,
      "Mn|W": 6.0,
      "Mn|Y": -1.0,
      "Mn|Zr": -15.0,
      "Mo|Nb": -6.0,
      "Mo|Ni": -7.0,
      "Mo|Os": -14.0,
      "Mo|Pd": -15.0,
      "Mo|Pt": -28.0,
      "Mo|Rh": -15.0,
      "Mo|Ru": -14.0,
      "Mo|Si": -35.0,
      "Mo|Ta": -5.0,
      "Mo|Ti": -4.0,
      "Mo|V": 0.0,
      "Mo|W": 0.0,
      "Mo|Y": 24.0,
      "Mo|Zr": -6.0,
      "Nb|Ni": -30.0,
      "Nb|Os": -39.0,
      "Nb|Pd": -53.0,
      "Nb|Pt": -67.0,
      "Nb|Rh": -46.0,
      "Nb|Ru": -41.0,
      "Nb|Si": -56.0,
      "Nb|Ta": 0.0,
      "Nb|Ti": 2.0,
      "Nb|V": -1.0,
      "Nb|W": -8.0,
      "Nb|Y": 30.0,
      "Nb|Zr": 4.0,
      "Ni|Os": 1.0,
      "Ni|Pd": 0.0,
      "Ni|Pt": -5.0,
      "Ni|Rh": -1.0,
      "Ni|Ru": 0.0,
      "Ni|Si": -40.0,
      "Ni|Ta": -29.0,
      "Ni|Ti": -35.0,
      "Ni|V": -18.0,
      "Ni|W": -3.0,
      "Ni|Y": -31.0,
      "Ni|Zr": -49.0,
      "Os|Pd": 8.0,
      "Os|Pt": 0.0,
      "Os|Rh": 2.0,
      "Os|Ru": 0.0,
      "Os|Si": -36.0,
      "Os|Ta": -38.0,
      "Os|Ti": -41.0,
      "Os|V": -23.0,
      "Os|W": -10.0,
      "Os|Y": -28.0,
      "Os|Zr": -55.0,
      "Pd|Pt": 2.0,
      "Pd|Rh": 2.0,
      "Pd|Ru": 6.0,
      "Pd|Si": -55.0,
      "Pd|Ta": -52.0,
      "Pd|Ti": -65.0,
      "Pd|V": -35.0,
      "Pd|W": -6.0,
      "Pd|Y": -84.0,
      "Pd|Zr": -91.0,
      "Pt|Rh": -2.0,
      "Pt|Ru": -1.0,
      "Pt|Si": -53.0,
      "Pt|Ta": -66.0,
      "Pt|Ti": -74.0,
      "Pt|V": -45.0,
      "Pt|W": -20.0,
      "Pt|Y": -83.0,
      "Pt|Zr": -100.0,
      "Rh|Ru": 1.0,
      "Rh|Si": -46.0,
      "Rh|Ta": -45.0,
      "Rh|Ti": -52.0,
      "Rh|V": -29.0,
      "Rh|W": -9.0,
      "Rh|Y": -54.0,
      "Rh|Zr": -72.0,
      "Ru|Si": -38.0,
      "Ru|Ta": -39.0,
      "Ru|Ti": -43.0,
      "Ru|V": -25.0,
      "Ru|W": -10.0,
      "Ru|Y": -34.0,
      "Ru|Zr": -59.0,
      "Si|Ta": -56.0,
      "Si|Ti": -66.0,
      "Si|V": -48.0,
      "Si|W": -31.0,
      "Si|Y": -73.0,
      "Si|Zr": -84.0,
      "Ta|Ti": 1.0,
      "Ta|V": -1.0,
      "Ta|W": -7.0,
      "Ta|Y": 27.0,
      "Ta|Zr": 3.0,
      "Ti|V": -2.0,
      "Ti|W": -6.0,
      "Ti|Y": 15.0,
      "Ti|Zr": 0.0,
      "V|W": -1.0,
      "V|Y": 17.0,
      "V|Zr": -4.0,
      "W|Y": 24.0,
      "W|Zr": -9.0,
      "Y|Zr": 9.0
    };

    function hasOwn(obj, key) {
      return Object.prototype.hasOwnProperty.call(obj, key);
    }

    function sortStrings(values) {
      return values.slice().sort(function (left, right) {
        if (left < right) {
          return -1;
        }
        if (left > right) {
          return 1;
        }
        return 0;
      });
    }

    function pairKey(elemA, elemB) {
      if (elemA < elemB) {
        return elemA + "|" + elemB;
      }
      return elemB + "|" + elemA;
    }

    function normalizeComposition(composition) {
      if (!composition || typeof composition !== "object") {
        throw new Error("composition must be a mapping of element to amount");
      }

      var total = 0.0;
      var norm = {};
      var key;
      var amount;

      for (key in composition) {
        if (!hasOwn(composition, key)) {
          continue;
        }
        amount = Number(composition[key]);
        if (isFinite(amount) && amount > 0) {
          norm[key] = amount;
          total += amount;
        }
      }

      if (total <= 0) {
        throw new Error("composition values must sum to a positive number");
      }

      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        norm[key] = norm[key] / total;
      }

      return norm;
    }

      function isNumericValue(value) {
        return typeof value === "number" && !Number.isNaN(value);
      }

    function ensureElementData(norm, elementData) {
      var missing = [];
      var key;
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        if (!elementData || !hasOwn(elementData, key)) {
          missing.push(key);
        }
      }
      if (missing.length) {
        throw new Error(
          "composition contains elements not in elemental data table: " + sortStrings(missing).join(", ")
        );
      }
    }

    function browserPairEnthalpy(elemA, elemB) {
      var paramsA;
      var paramsB;
      var pairType;
      var pConst;
      var qConst;
      var rVal;
      var dPhi;
      var dNws;
      var baseV23A;
      var baseV23B;
      var v23A;
      var v23B;
      var aA;
      var aB;
      var csA;
      var csB;
      var iter;
      var volumeFactor;
      var nwsAvgInv;
      var interfacialEnergy;

      if (elemA === elemB) {
        return 0.0;
      }

      paramsA = BROWSER_MIEDEMA_PARAMS[elemA];
      paramsB = BROWSER_MIEDEMA_PARAMS[elemB];
      if (!paramsA || !paramsB) {
        return null;
      }

      if (paramsA.cls === "TM" && paramsB.cls === "TM") {
        pairType = "TM-TM";
      } else if (paramsA.cls === "NTM" && paramsB.cls === "NTM") {
        pairType = "NTM-NTM";
      } else {
        pairType = "TM-NTM";
      }

      pConst = BROWSER_MIEDEMA_PAIR_P[pairType];
      qConst = pConst * BROWSER_MIEDEMA_QP_RATIO;
      rVal = 0.0;

      if (pairType !== "TM-TM") {
        rVal = (BROWSER_MIEDEMA_R_OVER_P[elemA] || 1.0) * (BROWSER_MIEDEMA_R_OVER_P[elemB] || 1.0) * pConst;
      }

      dPhi = paramsA.phi_star - paramsB.phi_star;
      dNws = paramsA.nws13 - paramsB.nws13;
      baseV23A = paramsA.V23;
      baseV23B = paramsB.V23;
      v23A = baseV23A;
      v23B = baseV23B;
      aA = BROWSER_MIEDEMA_A_VOL[elemA] || 0.04;
      aB = BROWSER_MIEDEMA_A_VOL[elemB] || 0.04;

      for (iter = 0; iter < 5; iter += 1) {
        csB = v23B / (v23A + v23B);
        csA = v23A / (v23A + v23B);
        v23A = baseV23A * (1.0 + aA * csB * dPhi);
        v23B = baseV23B * (1.0 - aB * csA * dPhi);
      }

      volumeFactor = (2.0 * v23A * v23B) / (v23A + v23B);
      nwsAvgInv = 0.5 * (1.0 / paramsA.nws13 + 1.0 / paramsB.nws13);
      interfacialEnergy = (-pConst * dPhi * dPhi + qConst * dNws * dNws - rVal) / nwsAvgInv;
      return volumeFactor * interfacialEnergy;
    }

    function browserMixingEnthalpy(composition) {
      var norm = normalizeComposition(composition);
      var missing = [];
      var key;
      var pairTerms;

      for (key in norm) {
        if (hasOwn(norm, key) && !hasOwn(BROWSER_MIEDEMA_PARAMS, key)) {
          missing.push(key);
        }
      }

      if (missing.length) {
        throw new Error(
          "composition contains elements not in browser Miedema calculator data: " + sortStrings(missing).join(", ")
        );
      }

      pairTerms = collectPairTerms(norm, browserPairEnthalpy);
      return pairTerms.total;
    }

    function browserOmega(composition, options) {
      var h = browserMixingEnthalpy(composition);
      if (h === 0.0) {
        return Infinity;
      }
      return (meltingTemperature(composition, options) * smix(composition)) / (Math.abs(h) * 1000.0);
    }

    function buildPairResolver(options) {
      var pairTable = options && options.pairTable ? options.pairTable : PAIR_ENTHALPIES;
      var overrides = options && options.pairEnthalpyOverrides ? options.pairEnthalpyOverrides : null;
      var fallback = options && options.pairEnthalpyResolver ? options.pairEnthalpyResolver : null;

      return function (elemA, elemB) {
        if (elemA === elemB) {
          return 0.0;
        }

        var key = pairKey(elemA, elemB);
        var value;

        if (overrides && hasOwn(overrides, key)) {
          value = Number(overrides[key]);
          if (isFinite(value)) {
            return value;
          }
        }

        if (pairTable && hasOwn(pairTable, key)) {
          return Number(pairTable[key]);
        }

        if (fallback) {
          value = Number(fallback(elemA, elemB, key));
          if (isFinite(value)) {
            return value;
          }
        }

        return null;
      };
    }

    function collectPairTerms(norm, resolver) {
      var elements = sortStrings(Object.keys(norm));
      var total = 0.0;
      var values = [];
      var rawValues = [];
      var missingPairs = [];
      var i;
      var j;
      var elemA;
      var elemB;
      var enthalpy;
      var pairValue;

      for (i = 0; i < elements.length; i += 1) {
        elemA = elements[i];
        for (j = i + 1; j < elements.length; j += 1) {
          elemB = elements[j];
          enthalpy = resolver(elemA, elemB);
          if (!isFinite(enthalpy)) {
            missingPairs.push(pairKey(elemA, elemB));
            continue;
          }

          pairValue = 4.0 * norm[elemA] * norm[elemB] * enthalpy;
          total += pairValue;
          values.push(pairValue);
          rawValues.push(enthalpy);
        }
      }

      return {
        total: total,
        values: values,
        rawValues: rawValues,
        missingPairs: missingPairs
      };
    }

    function sumByNorm(norm, elementData, keyName) {
      var total = 0.0;
      var key;
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        total += norm[key] * elementData[key][keyName];
      }
      return total;
    }

    function smixFromNormalized(norm) {
      var total = 0.0;
      var key;
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        total += norm[key] * Math.log(norm[key]);
      }
      return -R * total;
    }

    function deltaFromNormalized(norm, elementData) {
      var rBar = sumByNorm(norm, elementData, "radius");
      var inner = 0.0;
      var key;
      if (rBar <= 0) {
        throw new Error("mean atomic radius is zero or negative");
      }
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        inner += norm[key] * Math.pow(1.0 - elementData[key].radius / rBar, 2);
      }
      return 100.0 * Math.sqrt(Math.max(inner, 0.0));
    }

    function meltingTemperatureFromNormalized(norm, elementData) {
      return sumByNorm(norm, elementData, "melting");
    }

    function vecFromNormalized(norm, elementData) {
      return sumByNorm(norm, elementData, "valence");
    }

    function mansooriExcessEntropyFromNormalized(norm, packingFraction, elementData) {
      if (!(packingFraction > 0.0 && packingFraction < 1.0)) {
        throw new Error("packing_fraction must be between 0 and 1");
      }

      var elements = sortStrings(Object.keys(norm));
      var diameters = {};
      var sigma2 = 0.0;
      var sigma3 = 0.0;
      var pairTerm1 = 0.0;
      var pairTerm2 = 0.0;
      var i;
      var j;
      var elemA;
      var elemB;
      var diameterA;
      var diameterB;
      var coefficient;
      var zeta;
      var y1;
      var y2;
      var y3;

      for (i = 0; i < elements.length; i += 1) {
        elemA = elements[i];
        diameters[elemA] = 2.0 * elementData[elemA].radius;
        sigma2 += norm[elemA] * Math.pow(diameters[elemA], 2);
        sigma3 += norm[elemA] * Math.pow(diameters[elemA], 3);
      }

      for (i = 0; i < elements.length; i += 1) {
        elemA = elements[i];
        diameterA = diameters[elemA];
        for (j = i + 1; j < elements.length; j += 1) {
          elemB = elements[j];
          diameterB = diameters[elemB];
          coefficient = norm[elemA] * norm[elemB] * Math.pow(diameterA - diameterB, 2);
          pairTerm1 += (diameterA + diameterB) * coefficient;
          pairTerm2 += diameterA * diameterB * coefficient;
        }
      }

      zeta = 1.0 / (1.0 - packingFraction);
      y1 = sigma3 ? pairTerm1 / sigma3 : 0.0;
      y2 = sigma3 ? (sigma2 / Math.pow(sigma3, 2)) * pairTerm2 : 0.0;
      y3 = sigma3 ? Math.pow(sigma2, 3) / Math.pow(sigma3, 2) : 1.0;

      return R * (
        1.5 * (Math.pow(zeta, 2) - 1.0) * y1 +
        1.5 * Math.pow(zeta - 1.0, 2) * y2 -
        ((0.5 * (zeta - 1.0) * (zeta - 3.0)) + Math.log(zeta)) * (1.0 - y3)
      );
    }

    function sExcessFromNormalized(norm, elementData, packingFraction) {
      if (packingFraction !== null && packingFraction !== undefined) {
        return mansooriExcessEntropyFromNormalized(norm, Number(packingFraction), elementData);
      }
      return (
        mansooriExcessEntropyFromNormalized(norm, PACKING_FRACTION_BCC, elementData) +
        mansooriExcessEntropyFromNormalized(norm, PACKING_FRACTION_FCC, elementData)
      ) / 2.0;
    }

    function rulePredictionsFromDescriptors(descriptors, options) {
      var result = {
        yeh_smix: { threshold: null, verdict: null, value: descriptors.Smix },
        zhang_delta: { threshold: ZHANG_DELTA_THRESHOLD, verdict: null, value: descriptors.delta },
        guo_vec: { threshold: null, verdict: null, value: descriptors.VEC },
        yang_omega: { threshold: YANG_OMEGA_THRESHOLD, verdict: null, value: descriptors.Omega },
        king_phi: {
          threshold: options && options.kingThreshold !== undefined ? Number(options.kingThreshold) : KING_PHI_THRESHOLD,
          verdict: null,
          value: descriptors.Phi_king,
          temperature: descriptors.King_temperature_K
        },
        ye_phi: {
          threshold: options && options.yeThreshold !== undefined ? Number(options.yeThreshold) : YE_PHI_THRESHOLD,
          verdict: null,
          value: descriptors.Phi_ye
        }
      };

      if (isNumericValue(descriptors.Smix)) {
        if (descriptors.Smix > YEH_HEA_FACTOR * R) {
          result.yeh_smix.verdict = "HEA";
        } else if (descriptors.Smix >= R) {
          result.yeh_smix.verdict = "MEA";
        } else {
          result.yeh_smix.verdict = "dilute";
        }
      }

      if (isNumericValue(descriptors.delta)) {
        result.zhang_delta.verdict = descriptors.delta < result.zhang_delta.threshold ? "single-phase" : "multi-phase";
      }

      if (isNumericValue(descriptors.VEC)) {
        var roundedVec = Math.round(descriptors.VEC * 1000000) / 1000000;
        if (roundedVec >= GUO_VEC_FCC_THRESHOLD) {
          result.guo_vec.verdict = "FCC";
        } else if (roundedVec < GUO_VEC_BCC_THRESHOLD) {
          result.guo_vec.verdict = "BCC";
        } else {
          result.guo_vec.verdict = "mixed";
        }
      }

      if (isNumericValue(descriptors.Omega)) {
        result.yang_omega.verdict = descriptors.Omega > result.yang_omega.threshold ? "single-phase" : "multi-phase";
      }

      if (isNumericValue(result.king_phi.value)) {
        result.king_phi.verdict = result.king_phi.value > result.king_phi.threshold ? "solid_solution" : "intermetallic";
      }

      if (isNumericValue(result.ye_phi.value)) {
        result.ye_phi.verdict = result.ye_phi.value > result.ye_phi.threshold ? "solid_solution" : "intermetallic";
      }

      return result;
    }

    function calculateDescriptors(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      var warnings = [];
      var resolver = buildPairResolver(options);
      var pairTerms;
      var Tm;
      var Smix;
      var delta;
      var VEC;
      var Hmix;
      var Omega;
      var kingTemperature;
      var sExcess;
      var deltaGss;
      var deltaGmax;
      var phiKing;
      var phiYe;
      var descriptors;

      ensureElementData(norm, elementData);
      pairTerms = collectPairTerms(norm, resolver);

      if (pairTerms.missingPairs.length) {
        warnings.push(
          "Missing pair enthalpy data for " + pairTerms.missingPairs.join(", ") + "; values that depend on Hmix are unavailable."
        );
      }

      Tm = meltingTemperatureFromNormalized(norm, elementData);
      Smix = smixFromNormalized(norm);
      delta = deltaFromNormalized(norm, elementData);
      VEC = vecFromNormalized(norm, elementData);
      Hmix = pairTerms.missingPairs.length ? null : pairTerms.total;
      Omega = null;
      if (Hmix !== null) {
        if (Hmix === 0.0) {
          Omega = Infinity;
        } else {
          Omega = (Tm * Smix) / Math.abs(Hmix * 1000.0);
        }
      }

      kingTemperature = options && options.kingTemperature !== undefined && options.kingTemperature !== null
        ? Number(options.kingTemperature)
        : Tm;
      if (!(kingTemperature > 0)) {
        kingTemperature = Tm;
      }

      sExcess = sExcessFromNormalized(norm, elementData, options && options.packingFraction);
      deltaGss = null;
      deltaGmax = null;
      phiKing = null;
      phiYe = null;

      if (Hmix !== null) {
        deltaGss = Hmix - (kingTemperature * Smix) / 1000.0;
        deltaGmax = pairTerms.rawValues.length ? Math.min.apply(null, pairTerms.rawValues) : 0.0;
        phiKing = deltaGmax === 0.0 ? Infinity : deltaGss / (-Math.abs(deltaGmax));
        phiYe = Math.abs(sExcess) === 0.0 ? Infinity : (Smix - Math.abs(Hmix) * 1000.0 / Tm) / Math.abs(sExcess);
      }

      descriptors = {
        Smix: Smix,
        delta: delta,
        Tm_K: Tm,
        Tm_C: Tm - 273.15,
        Hmix: Hmix,
        VEC: VEC,
        Omega: Omega,
        H_compound: null,
        H_SS_total: null,
        H_SS_chem: null,
        H_SS_elast: null,
        H_SS_struct: null,
        H_AM_total: null,
        H_AM_chem: null,
        H_AM_topo: null,
        S_excess: sExcess,
        DeltaG_ss: deltaGss,
        DeltaG_max: deltaGmax,
        Phi_king: phiKing,
        Phi_ye: phiYe,
        King_temperature_K: kingTemperature
      };

      return {
        composition: norm,
        descriptors: descriptors,
        rules: rulePredictionsFromDescriptors(descriptors, options),
        warnings: warnings,
        missingPairs: pairTerms.missingPairs.slice()
      };
    }

    function smix(composition) {
      return smixFromNormalized(normalizeComposition(composition));
    }

    function delta(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      ensureElementData(norm, elementData);
      return deltaFromNormalized(norm, elementData);
    }

    function meltingTemperature(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      ensureElementData(norm, elementData);
      return meltingTemperatureFromNormalized(norm, elementData);
    }

    function vec(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      ensureElementData(norm, elementData);
      return vecFromNormalized(norm, elementData);
    }

    function mixingEnthalpy(composition, options) {
      var norm = normalizeComposition(composition);
      var pairTerms = collectPairTerms(norm, buildPairResolver(options));
      if (pairTerms.missingPairs.length) {
        throw new Error(
          "composition contains pairs not in Miedema pair table: " + pairTerms.missingPairs.join(", ")
        );
      }
      return pairTerms.total;
    }

    function omega(composition, options) {
      var tm = meltingTemperature(composition, options);
      var s = smix(composition);
      var h = mixingEnthalpy(composition, options);
      if (h === 0.0) {
        return Infinity;
      }
      return (tm * s) / Math.abs(h * 1000.0);
    }

    function sExcess(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      ensureElementData(norm, elementData);
      return sExcessFromNormalized(norm, elementData, options && options.packingFraction);
    }

    function deltaGSs(composition, options) {
      var temperature = options && options.temperature !== undefined && options.temperature !== null
        ? Number(options.temperature)
        : meltingTemperature(composition, options);
      return mixingEnthalpy(composition, options) - (temperature * smix(composition)) / 1000.0;
    }

    function deltaGMax(composition, options) {
      var norm = normalizeComposition(composition);
      var pairTerms = collectPairTerms(norm, buildPairResolver(options));
      if (pairTerms.missingPairs.length) {
        throw new Error(
          "composition contains pairs not in Miedema pair table: " + pairTerms.missingPairs.join(", ")
        );
      }
      return pairTerms.rawValues.length ? Math.min.apply(null, pairTerms.rawValues) : 0.0;
    }

    function phiKing(composition, options) {
      var gss = deltaGSs(composition, options);
      var gmax = deltaGMax(composition, options);
      if (gmax === 0.0) {
        return Infinity;
      }
      return gss / (-Math.abs(gmax));
    }

    function phiYe(composition, options) {
      var tm = meltingTemperature(composition, options);
      var numerator = smix(composition) - Math.abs(mixingEnthalpy(composition, options)) * 1000.0 / tm;
      var denominator = Math.abs(sExcess(composition, options));
      if (denominator === 0.0) {
        return Infinity;
      }
      return numerator / denominator;
    }

    function predictYehSmix(composition) {
      return rulePredictionsFromDescriptors({
        Smix: smix(composition),
        delta: NaN,
        VEC: NaN,
        Omega: NaN,
        Phi_king: NaN,
        Phi_ye: NaN,
        King_temperature_K: NaN
      }, null).yeh_smix.verdict;
    }

    function predictZhangDelta(composition, options) {
      return rulePredictionsFromDescriptors({
        Smix: NaN,
        delta: delta(composition, options),
        VEC: NaN,
        Omega: NaN,
        Phi_king: NaN,
        Phi_ye: NaN,
        King_temperature_K: NaN
      }, null).zhang_delta.verdict;
    }

    function predictGuoVec(composition, options) {
      return rulePredictionsFromDescriptors({
        Smix: NaN,
        delta: NaN,
        VEC: vec(composition, options),
        Omega: NaN,
        Phi_king: NaN,
        Phi_ye: NaN,
        King_temperature_K: NaN
      }, null).guo_vec.verdict;
    }

    function predictYangOmega(composition, options) {
      return rulePredictionsFromDescriptors({
        Smix: NaN,
        delta: NaN,
        VEC: NaN,
        Omega: omega(composition, options),
        Phi_king: NaN,
        Phi_ye: NaN,
        King_temperature_K: NaN
      }, null).yang_omega.verdict;
    }

    function predictKingPhi(composition, options) {
      var predictionOptions = options || {};
      return rulePredictionsFromDescriptors({
        Smix: NaN,
        delta: NaN,
        VEC: NaN,
        Omega: NaN,
        Phi_king: phiKing(composition, { temperature: predictionOptions.temperature, pairTable: predictionOptions.pairTable, pairEnthalpyOverrides: predictionOptions.pairEnthalpyOverrides, pairEnthalpyResolver: predictionOptions.pairEnthalpyResolver, elementData: predictionOptions.elementData }),
        Phi_ye: NaN,
        King_temperature_K: predictionOptions.temperature !== undefined && predictionOptions.temperature !== null ? Number(predictionOptions.temperature) : meltingTemperature(composition, predictionOptions)
      }, { kingThreshold: predictionOptions.threshold }).king_phi.verdict;
    }

    function predictYePhi(composition, options) {
      var predictionOptions = options || {};
      return rulePredictionsFromDescriptors({
        Smix: NaN,
        delta: NaN,
        VEC: NaN,
        Omega: NaN,
        Phi_king: NaN,
        Phi_ye: phiYe(composition, predictionOptions),
        King_temperature_K: NaN
      }, { yeThreshold: predictionOptions.threshold }).ye_phi.verdict;
    }

    return {
      R: R,
      KING_PHI_THRESHOLD: KING_PHI_THRESHOLD,
      YE_PHI_THRESHOLD: YE_PHI_THRESHOLD,
      PACKING_FRACTION_BCC: PACKING_FRACTION_BCC,
      PACKING_FRACTION_FCC: PACKING_FRACTION_FCC,
      ZHANG_DELTA_THRESHOLD: ZHANG_DELTA_THRESHOLD,
      YANG_OMEGA_THRESHOLD: YANG_OMEGA_THRESHOLD,
      GUO_VEC_FCC_THRESHOLD: GUO_VEC_FCC_THRESHOLD,
      GUO_VEC_BCC_THRESHOLD: GUO_VEC_BCC_THRESHOLD,
      ELEMENT_DATA: DEFAULT_ELEMENT_DATA,
      PAIR_ENTHALPIES: PAIR_ENTHALPIES,
      browserPairEnthalpy: browserPairEnthalpy,
      browserMixingEnthalpy: browserMixingEnthalpy,
      browserOmega: browserOmega,
      pairKey: pairKey,
      normalizeComposition: normalizeComposition,
      calculateDescriptors: calculateDescriptors,
      rulePredictionsFromDescriptors: rulePredictionsFromDescriptors,
      smix: smix,
      delta: delta,
      meltingTemperature: meltingTemperature,
      vec: vec,
      mixingEnthalpy: mixingEnthalpy,
      omega: omega,
      sExcess: sExcess,
      deltaGSs: deltaGSs,
      deltaGMax: deltaGMax,
      phiKing: phiKing,
      phiYe: phiYe,
      predictYehSmix: predictYehSmix,
      predictZhangDelta: predictZhangDelta,
      predictGuoVec: predictGuoVec,
      predictYangOmega: predictYangOmega,
      predictKingPhi: predictKingPhi,
      predictYePhi: predictYePhi
    };
  }
);