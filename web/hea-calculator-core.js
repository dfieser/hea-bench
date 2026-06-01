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

    // 30-element coverage (atomic radius, melting point, valence). The
    // original 24 (v1.1) match the Python elemental data table
    // byte-for-byte; the six v1.2 additions (Au, Li, Mg, Re, Sn, Zn)
    // were added alongside the Python library for parity.
    var DEFAULT_ELEMENT_DATA = {
      Ag: { radius: 144.0, melting: 1234.93, valence: 11 },
      Al: { radius: 143.0, melting: 933.47, valence: 3 },
      Au: { radius: 144.0, melting: 1337.33, valence: 11 },
      Co: { radius: 125.0, melting: 1768.0, valence: 9 },
      Cr: { radius: 129.0, melting: 2180.0, valence: 6 },
      Cu: { radius: 128.0, melting: 1357.77, valence: 11 },
      Fe: { radius: 126.0, melting: 1811.0, valence: 8 },
      Hf: { radius: 159.0, melting: 2506.0, valence: 4 },
      Ir: { radius: 136.0, melting: 2719.0, valence: 9 },
      Li: { radius: 157.0, melting: 453.65, valence: 1 },
      Mg: { radius: 160.0, melting: 923.15, valence: 2 },
      Mn: { radius: 135.7, melting: 1519.0, valence: 7 },
      Mo: { radius: 139.0, melting: 2896.0, valence: 6 },
      Nb: { radius: 147.0, melting: 2750.0, valence: 5 },
      Ni: { radius: 125.0, melting: 1728.0, valence: 10 },
      Os: { radius: 135.0, melting: 3306.0, valence: 8 },
      Pd: { radius: 137.0, melting: 1828.0, valence: 10 },
      Pt: { radius: 139.0, melting: 2041.4, valence: 10 },
      Re: { radius: 137.0, melting: 3459.15, valence: 7 },
      Rh: { radius: 134.0, melting: 2237.0, valence: 9 },
      Ru: { radius: 134.0, melting: 2607.0, valence: 8 },
      Si: { radius: 111.0, melting: 1687.0, valence: 4 },
      Sn: { radius: 158.0, melting: 505.08, valence: 4 },
      Ta: { radius: 147.0, melting: 3290.0, valence: 5 },
      Ti: { radius: 147.0, melting: 1941.0, valence: 4 },
      V: { radius: 135.0, melting: 2183.0, valence: 5 },
      W: { radius: 141.0, melting: 3695.0, valence: 6 },
      Y: { radius: 182.0, melting: 1799.0, valence: 3 },
      Zn: { radius: 137.0, melting: 692.68, valence: 12 },
      Zr: { radius: 160.0, melting: 2128.0, valence: 4 }
    };

    // 435 pairs = C(30, 2). Matminer-derived Miedema binary mixing
    // enthalpies for the 30 elements covered by ELEMENTAL_DATA.
    var PAIR_ENTHALPIES = {
      "Ag|Al": -4.0,
      "Ag|Au": -6.0,
      "Ag|Co": 19.0,
      "Ag|Cr": 27.0,
      "Ag|Cu": 2.0,
      "Ag|Fe": 28.0,
      "Ag|Hf": -13.0,
      "Ag|Ir": 16.0,
      "Ag|Li": -16.0,
      "Ag|Mg": -10.0,
      "Ag|Mn": 13.0,
      "Ag|Mo": 37.0,
      "Ag|Nb": 16.0,
      "Ag|Ni": 15.0,
      "Ag|Os": 28.0,
      "Ag|Pd": -7.0,
      "Ag|Pt": -1.0,
      "Ag|Re": 38.0,
      "Ag|Rh": 10.0,
      "Ag|Ru": 23.0,
      "Ag|Si": -20.0,
      "Ag|Sn": -3.0,
      "Ag|Ta": 15.0,
      "Ag|Ti": -2.0,
      "Ag|V": 17.0,
      "Ag|W": 43.0,
      "Ag|Y": -29.0,
      "Ag|Zn": -4.0,
      "Ag|Zr": -20.0,
      "Al|Au": -22.0,
      "Al|Co": -19.0,
      "Al|Cr": -10.0,
      "Al|Cu": -1.0,
      "Al|Fe": -11.0,
      "Al|Hf": -39.0,
      "Al|Ir": -30.0,
      "Al|Li": -4.0,
      "Al|Mg": -2.0,
      "Al|Mn": -19.0,
      "Al|Mo": -5.0,
      "Al|Nb": -18.0,
      "Al|Ni": -22.0,
      "Al|Os": -18.0,
      "Al|Pd": -46.0,
      "Al|Pt": -44.0,
      "Al|Re": -9.0,
      "Al|Rh": -32.0,
      "Al|Ru": -21.0,
      "Al|Si": -19.0,
      "Al|Sn": 4.0,
      "Al|Ta": -19.0,
      "Al|Ti": -30.0,
      "Al|V": -16.0,
      "Al|W": -2.0,
      "Al|Y": -38.0,
      "Al|Zn": 1.0,
      "Al|Zr": -44.0,
      "Au|Co": 7.0,
      "Au|Cr": 0.0,
      "Au|Cu": -9.0,
      "Au|Fe": 8.0,
      "Au|Hf": -63.0,
      "Au|Ir": 13.0,
      "Au|Li": -37.0,
      "Au|Mg": -32.0,
      "Au|Mn": -11.0,
      "Au|Mo": 3.0,
      "Au|Nb": -32.0,
      "Au|Ni": 7.0,
      "Au|Os": 18.0,
      "Au|Pd": 0.0,
      "Au|Pt": 4.0,
      "Au|Re": 20.0,
      "Au|Rh": 7.0,
      "Au|Ru": 15.0,
      "Au|Si": -30.0,
      "Au|Sn": -10.0,
      "Au|Ta": -32.0,
      "Au|Ti": -47.0,
      "Au|V": -19.0,
      "Au|W": 12.0,
      "Au|Y": -74.0,
      "Au|Zn": -16.0,
      "Au|Zr": -74.0,
      "Co|Cr": -4.0,
      "Co|Cu": 6.0,
      "Co|Fe": -1.0,
      "Co|Hf": -35.0,
      "Co|Ir": -3.0,
      "Co|Li": 8.0,
      "Co|Mg": 3.0,
      "Co|Mn": -5.0,
      "Co|Mo": -5.0,
      "Co|Nb": -25.0,
      "Co|Ni": 0.0,
      "Co|Os": 0.0,
      "Co|Pd": -1.0,
      "Co|Pt": -7.0,
      "Co|Re": 2.0,
      "Co|Rh": -2.0,
      "Co|Ru": -1.0,
      "Co|Si": -38.0,
      "Co|Sn": 0.0,
      "Co|Ta": -24.0,
      "Co|Ti": -28.0,
      "Co|V": -14.0,
      "Co|W": -1.0,
      "Co|Y": -22.0,
      "Co|Zn": -5.0,
      "Co|Zr": -41.0,
      "Cr|Cu": 12.0,
      "Cr|Fe": -1.0,
      "Cr|Hf": -9.0,
      "Cr|Ir": -18.0,
      "Cr|Li": 35.0,
      "Cr|Mg": 24.0,
      "Cr|Mn": 2.0,
      "Cr|Mo": 0.0,
      "Cr|Nb": -7.0,
      "Cr|Ni": -7.0,
      "Cr|Os": -11.0,
      "Cr|Pd": -15.0,
      "Cr|Pt": -24.0,
      "Cr|Re": -4.0,
      "Cr|Rh": -13.0,
      "Cr|Ru": -12.0,
      "Cr|Si": -37.0,
      "Cr|Sn": 10.0,
      "Cr|Ta": -7.0,
      "Cr|Ti": -7.0,
      "Cr|V": -2.0,
      "Cr|W": 1.0,
      "Cr|Y": 11.0,
      "Cr|Zn": 5.0,
      "Cr|Zr": -12.0,
      "Cu|Fe": 13.0,
      "Cu|Hf": -17.0,
      "Cu|Ir": 0.0,
      "Cu|Li": -5.0,
      "Cu|Mg": -3.0,
      "Cu|Mn": 4.0,
      "Cu|Mo": 19.0,
      "Cu|Nb": 3.0,
      "Cu|Ni": 4.0,
      "Cu|Os": 10.0,
      "Cu|Pd": -14.0,
      "Cu|Pt": -12.0,
      "Cu|Re": 18.0,
      "Cu|Rh": -2.0,
      "Cu|Ru": 7.0,
      "Cu|Si": -19.0,
      "Cu|Sn": 7.0,
      "Cu|Ta": 2.0,
      "Cu|Ti": -9.0,
      "Cu|V": 5.0,
      "Cu|W": 22.0,
      "Cu|Y": -22.0,
      "Cu|Zn": 1.0,
      "Cu|Zr": -23.0,
      "Fe|Hf": -21.0,
      "Fe|Ir": -9.0,
      "Fe|Li": 26.0,
      "Fe|Mg": 18.0,
      "Fe|Mn": 0.0,
      "Fe|Mo": -2.0,
      "Fe|Nb": -16.0,
      "Fe|Ni": -2.0,
      "Fe|Os": -4.0,
      "Fe|Pd": -4.0,
      "Fe|Pt": -13.0,
      "Fe|Re": 0.0,
      "Fe|Rh": -5.0,
      "Fe|Ru": -5.0,
      "Fe|Si": -35.0,
      "Fe|Sn": 11.0,
      "Fe|Ta": -15.0,
      "Fe|Ti": -17.0,
      "Fe|V": -7.0,
      "Fe|W": 0.0,
      "Fe|Y": -1.0,
      "Fe|Zn": 4.0,
      "Fe|Zr": -25.0,
      "Hf|Ir": -68.0,
      "Hf|Li": 30.0,
      "Hf|Mg": 10.0,
      "Hf|Mn": -12.0,
      "Hf|Mo": -4.0,
      "Hf|Nb": 4.0,
      "Hf|Ni": -42.0,
      "Hf|Os": -48.0,
      "Hf|Pd": -80.0,
      "Hf|Pt": -90.0,
      "Hf|Re": -30.0,
      "Hf|Rh": -63.0,
      "Hf|Ru": -52.0,
      "Hf|Si": -77.0,
      "Hf|Sn": -35.0,
      "Hf|Ta": 3.0,
      "Hf|Ti": 0.0,
      "Hf|V": -2.0,
      "Hf|W": -6.0,
      "Hf|Y": 11.0,
      "Hf|Zn": -24.0,
      "Hf|Zr": 0.0,
      "Ir|Li": -9.0,
      "Ir|Mg": -13.0,
      "Ir|Mn": -18.0,
      "Ir|Mo": -21.0,
      "Ir|Nb": -53.0,
      "Ir|Ni": -2.0,
      "Ir|Os": -1.0,
      "Ir|Pd": 6.0,
      "Ir|Pt": 0.0,
      "Ir|Re": -3.0,
      "Ir|Rh": 1.0,
      "Ir|Ru": -1.0,
      "Ir|Si": -43.0,
      "Ir|Sn": -5.0,
      "Ir|Ta": -52.0,
      "Ir|Ti": -57.0,
      "Ir|V": -34.0,
      "Ir|W": -16.0,
      "Ir|Y": -53.0,
      "Ir|Zn": -13.0,
      "Ir|Zr": -76.0,
      "Li|Mg": 0.0,
      "Li|Mn": 19.0,
      "Li|Mo": 49.0,
      "Li|Nb": 51.0,
      "Li|Ni": 1.0,
      "Li|Os": 11.0,
      "Li|Pd": -40.0,
      "Li|Pt": -33.0,
      "Li|Re": 29.0,
      "Li|Rh": -14.0,
      "Li|Ru": 5.0,
      "Li|Si": -30.0,
      "Li|Sn": -18.0,
      "Li|Ta": 48.0,
      "Li|Ti": 34.0,
      "Li|V": 37.0,
      "Li|W": 50.0,
      "Li|Y": 8.0,
      "Li|Zn": -7.0,
      "Li|Zr": 27.0,
      "Mg|Mn": 10.0,
      "Mg|Mo": 36.0,
      "Mg|Nb": 32.0,
      "Mg|Ni": -4.0,
      "Mg|Os": 5.0,
      "Mg|Pd": -40.0,
      "Mg|Pt": -35.0,
      "Mg|Re": 21.0,
      "Mg|Rh": -17.0,
      "Mg|Ru": 0.0,
      "Mg|Si": -26.0,
      "Mg|Sn": -9.0,
      "Mg|Ta": 30.0,
      "Mg|Ti": 16.0,
      "Mg|V": 23.0,
      "Mg|W": 38.0,
      "Mg|Y": -6.0,
      "Mg|Zn": -4.0,
      "Mg|Zr": 6.0,
      "Mn|Mo": 5.0,
      "Mn|Nb": -4.0,
      "Mn|Ni": -8.0,
      "Mn|Os": -9.0,
      "Mn|Pd": -23.0,
      "Mn|Pt": -28.0,
      "Mn|Re": -1.0,
      "Mn|Rh": -16.0,
      "Mn|Ru": -11.0,
      "Mn|Si": -45.0,
      "Mn|Sn": -7.0,
      "Mn|Ta": -4.0,
      "Mn|Ti": -8.0,
      "Mn|V": -1.0,
      "Mn|W": 6.0,
      "Mn|Y": -1.0,
      "Mn|Zn": -6.0,
      "Mn|Zr": -15.0,
      "Mo|Nb": -6.0,
      "Mo|Ni": -7.0,
      "Mo|Os": -14.0,
      "Mo|Pd": -15.0,
      "Mo|Pt": -28.0,
      "Mo|Re": -7.0,
      "Mo|Rh": -15.0,
      "Mo|Ru": -14.0,
      "Mo|Si": -35.0,
      "Mo|Sn": 20.0,
      "Mo|Ta": -5.0,
      "Mo|Ti": -4.0,
      "Mo|V": 0.0,
      "Mo|W": 0.0,
      "Mo|Y": 24.0,
      "Mo|Zn": 12.0,
      "Mo|Zr": -6.0,
      "Nb|Ni": -30.0,
      "Nb|Os": -39.0,
      "Nb|Pd": -53.0,
      "Nb|Pt": -67.0,
      "Nb|Re": -26.0,
      "Nb|Rh": -46.0,
      "Nb|Ru": -41.0,
      "Nb|Si": -56.0,
      "Nb|Sn": -1.0,
      "Nb|Ta": 0.0,
      "Nb|Ti": 2.0,
      "Nb|V": -1.0,
      "Nb|W": -8.0,
      "Nb|Y": 30.0,
      "Nb|Zn": -1.0,
      "Nb|Zr": 4.0,
      "Ni|Os": 1.0,
      "Ni|Pd": 0.0,
      "Ni|Pt": -5.0,
      "Ni|Re": 2.0,
      "Ni|Rh": -1.0,
      "Ni|Ru": 0.0,
      "Ni|Si": -40.0,
      "Ni|Sn": -4.0,
      "Ni|Ta": -29.0,
      "Ni|Ti": -35.0,
      "Ni|V": -18.0,
      "Ni|W": -3.0,
      "Ni|Y": -31.0,
      "Ni|Zn": -9.0,
      "Ni|Zr": -49.0,
      "Os|Pd": 8.0,
      "Os|Pt": 0.0,
      "Os|Re": -1.0,
      "Os|Rh": 2.0,
      "Os|Ru": 0.0,
      "Os|Si": -36.0,
      "Os|Sn": 9.0,
      "Os|Ta": -38.0,
      "Os|Ti": -41.0,
      "Os|V": -23.0,
      "Os|W": -10.0,
      "Os|Y": -28.0,
      "Os|Zn": -1.0,
      "Os|Zr": -55.0,
      "Pd|Pt": 2.0,
      "Pd|Re": 6.0,
      "Pd|Rh": 2.0,
      "Pd|Ru": 6.0,
      "Pd|Si": -55.0,
      "Pd|Sn": -34.0,
      "Pd|Ta": -52.0,
      "Pd|Ti": -65.0,
      "Pd|V": -35.0,
      "Pd|W": -6.0,
      "Pd|Y": -84.0,
      "Pd|Zn": -33.0,
      "Pd|Zr": -91.0,
      "Pt|Re": -4.0,
      "Pt|Rh": -2.0,
      "Pt|Ru": -1.0,
      "Pt|Si": -53.0,
      "Pt|Sn": -25.0,
      "Pt|Ta": -66.0,
      "Pt|Ti": -74.0,
      "Pt|V": -45.0,
      "Pt|W": -20.0,
      "Pt|Y": -83.0,
      "Pt|Zn": -29.0,
      "Pt|Zr": -100.0,
      "Re|Rh": 1.0,
      "Re|Ru": -1.0,
      "Re|Si": -31.0,
      "Re|Sn": 20.0,
      "Re|Ta": -24.0,
      "Re|Ti": -25.0,
      "Re|V": -13.0,
      "Re|W": -4.0,
      "Re|Y": -4.0,
      "Re|Zn": 8.0,
      "Re|Zr": -35.0,
      "Rh|Ru": 1.0,
      "Rh|Si": -46.0,
      "Rh|Sn": -13.0,
      "Rh|Ta": -45.0,
      "Rh|Ti": -52.0,
      "Rh|V": -29.0,
      "Rh|W": -9.0,
      "Rh|Y": -54.0,
      "Rh|Zn": -17.0,
      "Rh|Zr": -72.0,
      "Ru|Si": -38.0,
      "Ru|Sn": 4.0,
      "Ru|Ta": -39.0,
      "Ru|Ti": -43.0,
      "Ru|V": -25.0,
      "Ru|W": -10.0,
      "Ru|Y": -34.0,
      "Ru|Zn": -5.0,
      "Ru|Zr": -59.0,
      "Si|Sn": -11.0,
      "Si|Ta": -56.0,
      "Si|Ti": -66.0,
      "Si|V": -48.0,
      "Si|W": -31.0,
      "Si|Y": -73.0,
      "Si|Zn": -18.0,
      "Si|Zr": -84.0,
      "Sn|Ta": -3.0,
      "Sn|Ti": -21.0,
      "Sn|V": -1.0,
      "Sn|W": 27.0,
      "Sn|Y": -51.0,
      "Sn|Zn": 1.0,
      "Sn|Zr": -43.0,
      "Ta|Ti": 1.0,
      "Ta|V": -1.0,
      "Ta|W": -7.0,
      "Ta|Y": 27.0,
      "Ta|Zn": -3.0,
      "Ta|Zr": 3.0,
      "Ti|V": -2.0,
      "Ti|W": -6.0,
      "Ti|Y": 15.0,
      "Ti|Zn": -15.0,
      "Ti|Zr": 0.0,
      "V|W": -1.0,
      "V|Y": 17.0,
      "V|Zn": -2.0,
      "V|Zr": -4.0,
      "W|Y": 24.0,
      "W|Zn": 15.0,
      "W|Zr": -9.0,
      "Y|Zn": -31.0,
      "Y|Zr": 9.0,
      "Zn|Zr": -29.0
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