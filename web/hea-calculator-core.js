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
    var SINGH_LAMBDA_SS = 0.96;
    var SINGH_LAMBDA_IM = 0.24;
    var WANG_GAMMA_THRESHOLD = 1.175;
    var ANDREOLI_FCC_MAX = 6.05;
    var ANDREOLI_BCC_MAX = 22.0;
    var SENKOV_K2 = 0.6;
    var TSAI_SIGMA_VEC_MIN = 6.88;
    var TSAI_SIGMA_VEC_MAX = 7.84;
    var SHEIKH_DUCTILE_VEC = 4.5;
    var SHEIKH_BRITTLE_VEC = 4.6;
    var SIGMA_FORMER_ELEMENTS = { Cr: true, V: true };

    // 55-element coverage (atomic radius, melting point, valence,
    // Pauling electronegativity).
    // Generated from the Python library's ELEMENTAL_DATA by
    // tests/data/_sync_js_tables.py — do not edit by hand; the
    // parity test asserts the two tables agree.
    var DEFAULT_ELEMENT_DATA = {
      Ag: { radius: 144.0, melting: 1234.93, valence: 11, chi: 1.93 },
      Al: { radius: 143.0, melting: 933.47, valence: 3, chi: 1.61 },
      Au: { radius: 144.0, melting: 1337.33, valence: 11, chi: 2.54 },
      Be: { radius: 112.0, melting: 1560.0, valence: 2, chi: 1.57 },
      Bi: { radius: 168.9, melting: 544.55, valence: 5, chi: 2.02 },
      Ca: { radius: 197.0, melting: 1115.0, valence: 2, chi: 1.0 },
      Ce: { radius: 182.0, melting: 1071.0, valence: 3, chi: 1.12 },
      Co: { radius: 125.0, melting: 1768.0, valence: 9, chi: 1.88 },
      Cr: { radius: 129.0, melting: 2180.0, valence: 6, chi: 1.66 },
      Cu: { radius: 128.0, melting: 1357.77, valence: 11, chi: 1.9 },
      Dy: { radius: 177.5, melting: 1685.0, valence: 3, chi: 1.22 },
      Er: { radius: 175.8, melting: 1802.0, valence: 3, chi: 1.24 },
      Fe: { radius: 126.0, melting: 1811.0, valence: 8, chi: 1.83 },
      Ga: { radius: 135.3, melting: 302.91, valence: 3, chi: 1.81 },
      Gd: { radius: 180.2, melting: 1585.0, valence: 3, chi: 1.2 },
      Ge: { radius: 124.0, melting: 1211.4, valence: 4, chi: 2.01 },
      Hf: { radius: 159.0, melting: 2506.0, valence: 4, chi: 1.3 },
      Ho: { radius: 176.7, melting: 1745.0, valence: 3, chi: 1.23 },
      In: { radius: 167.0, melting: 429.7, valence: 3, chi: 1.78 },
      Ir: { radius: 136.0, melting: 2719.0, valence: 9, chi: 2.2 },
      La: { radius: 188.0, melting: 1193.0, valence: 3, chi: 1.1 },
      Li: { radius: 157.0, melting: 453.65, valence: 1, chi: 0.98 },
      Lu: { radius: 173.5, melting: 1936.0, valence: 3, chi: 1.27 },
      Mg: { radius: 160.0, melting: 923.15, valence: 2, chi: 1.31 },
      Mn: { radius: 135.7, melting: 1519.0, valence: 7, chi: 1.55 },
      Mo: { radius: 139.0, melting: 2896.0, valence: 6, chi: 2.16 },
      Nb: { radius: 147.0, melting: 2750.0, valence: 5, chi: 1.6 },
      Nd: { radius: 182.2, melting: 1289.0, valence: 3, chi: 1.14 },
      Ni: { radius: 125.0, melting: 1728.0, valence: 10, chi: 1.91 },
      Os: { radius: 135.0, melting: 3306.0, valence: 8, chi: 2.2 },
      Pb: { radius: 175.0, melting: 600.61, valence: 4, chi: 2.33 },
      Pd: { radius: 137.0, melting: 1828.0, valence: 10, chi: 2.2 },
      Pr: { radius: 182.8, melting: 1204.0, valence: 3, chi: 1.13 },
      Pt: { radius: 139.0, melting: 2041.4, valence: 10, chi: 2.28 },
      Re: { radius: 137.0, melting: 3459.15, valence: 7, chi: 1.9 },
      Rh: { radius: 134.0, melting: 2237.0, valence: 9, chi: 2.28 },
      Ru: { radius: 134.0, melting: 2607.0, valence: 8, chi: 2.2 },
      Sb: { radius: 157.1, melting: 903.78, valence: 5, chi: 2.05 },
      Sc: { radius: 164.0, melting: 1814.0, valence: 3, chi: 1.36 },
      Si: { radius: 111.0, melting: 1687.0, valence: 4, chi: 1.9 },
      Sm: { radius: 180.2, melting: 1345.0, valence: 3, chi: 1.17 },
      Sn: { radius: 158.0, melting: 505.08, valence: 4, chi: 1.96 },
      Sr: { radius: 215.1, melting: 1050.0, valence: 2, chi: 0.95 },
      Ta: { radius: 147.0, melting: 3290.0, valence: 5, chi: 1.5 },
      Tb: { radius: 178.3, melting: 1632.0, valence: 3, chi: 1.1 },
      Th: { radius: 179.8, melting: 2023.0, valence: 4, chi: 1.3 },
      Ti: { radius: 147.0, melting: 1941.0, valence: 4, chi: 1.54 },
      Tm: { radius: 174.7, melting: 1818.0, valence: 3, chi: 1.25 },
      U: { radius: 154.3, melting: 1408.0, valence: 6, chi: 1.38 },
      V: { radius: 135.0, melting: 2183.0, valence: 5, chi: 1.63 },
      W: { radius: 141.0, melting: 3695.0, valence: 6, chi: 2.36 },
      Y: { radius: 182.0, melting: 1799.0, valence: 3, chi: 1.22 },
      Yb: { radius: 193.9, melting: 1097.0, valence: 2, chi: 1.1 },
      Zn: { radius: 137.0, melting: 692.68, valence: 12, chi: 1.65 },
      Zr: { radius: 160.0, melting: 2128.0, valence: 4, chi: 1.33 }
    };

    // 1484 pairs = C(55, 2) minus 1 vendored-table gap(s)
    // (Th-U). Matminer-derived Miedema binary mixing
    // enthalpies for the 55 elements covered by ELEMENTAL_DATA.
    // Generated from the Python pair table by tests/data/_sync_js_tables.py.
    var PAIR_ENTHALPIES = {
      "Ag|Al": -4.0,
      "Ag|Au": -6.0,
      "Ag|Be": 6.0,
      "Ag|Bi": 2.0,
      "Ag|Ca": -28.0,
      "Ag|Ce": -30.0,
      "Ag|Co": 19.0,
      "Ag|Cr": 27.0,
      "Ag|Cu": 2.0,
      "Ag|Dy": -29.0,
      "Ag|Er": -29.0,
      "Ag|Fe": 28.0,
      "Ag|Ga": -5.0,
      "Ag|Gd": -29.0,
      "Ag|Ge": -17.5,
      "Ag|Hf": -13.0,
      "Ag|Ho": -29.0,
      "Ag|In": -2.0,
      "Ag|Ir": 16.0,
      "Ag|La": -30.0,
      "Ag|Li": -16.0,
      "Ag|Lu": -30.0,
      "Ag|Mg": -10.0,
      "Ag|Mn": 13.0,
      "Ag|Mo": 37.0,
      "Ag|Nb": 16.0,
      "Ag|Nd": -29.0,
      "Ag|Ni": 15.0,
      "Ag|Os": 28.0,
      "Ag|Pb": 3.0,
      "Ag|Pd": -7.0,
      "Ag|Pr": -30.0,
      "Ag|Pt": -1.0,
      "Ag|Re": 38.0,
      "Ag|Rh": 10.0,
      "Ag|Ru": 23.0,
      "Ag|Sb": -4.0,
      "Ag|Sc": -28.0,
      "Ag|Si": -20.0,
      "Ag|Sm": -30.0,
      "Ag|Sn": -3.0,
      "Ag|Sr": -27.0,
      "Ag|Ta": 15.0,
      "Ag|Tb": -29.0,
      "Ag|Th": -29.0,
      "Ag|Ti": -2.0,
      "Ag|Tm": -29.0,
      "Ag|U": -6.0,
      "Ag|V": 17.0,
      "Ag|W": 43.0,
      "Ag|Y": -29.0,
      "Ag|Yb": -28.0,
      "Ag|Zn": -4.0,
      "Ag|Zr": -20.0,
      "Al|Au": -22.0,
      "Al|Be": 0.0,
      "Al|Bi": 10.0,
      "Al|Ca": -20.0,
      "Al|Ce": -38.0,
      "Al|Co": -19.0,
      "Al|Cr": -10.0,
      "Al|Cu": -1.0,
      "Al|Dy": -38.0,
      "Al|Er": -38.0,
      "Al|Fe": -11.0,
      "Al|Ga": 1.0,
      "Al|Gd": -39.0,
      "Al|Ge": -14.5,
      "Al|Hf": -39.0,
      "Al|Ho": -38.0,
      "Al|In": 7.0,
      "Al|Ir": -30.0,
      "Al|La": -38.0,
      "Al|Li": -4.0,
      "Al|Lu": -39.0,
      "Al|Mg": -2.0,
      "Al|Mn": -19.0,
      "Al|Mo": -5.0,
      "Al|Nb": -18.0,
      "Al|Nd": -38.0,
      "Al|Ni": -22.0,
      "Al|Os": -18.0,
      "Al|Pb": 10.0,
      "Al|Pd": -46.0,
      "Al|Pr": -38.0,
      "Al|Pt": -44.0,
      "Al|Re": -9.0,
      "Al|Rh": -32.0,
      "Al|Ru": -21.0,
      "Al|Sb": 2.0,
      "Al|Sc": -38.0,
      "Al|Si": -19.0,
      "Al|Sm": -38.0,
      "Al|Sn": 4.0,
      "Al|Sr": -18.0,
      "Al|Ta": -19.0,
      "Al|Tb": -39.0,
      "Al|Th": -40.0,
      "Al|Ti": -30.0,
      "Al|Tm": -38.0,
      "Al|U": -33.0,
      "Al|V": -16.0,
      "Al|W": -2.0,
      "Al|Y": -38.0,
      "Al|Yb": -20.0,
      "Al|Zn": 1.0,
      "Al|Zr": -44.0,
      "Au|Be": 0.0,
      "Au|Bi": 2.0,
      "Au|Ca": -60.0,
      "Au|Ce": -73.0,
      "Au|Co": 7.0,
      "Au|Cr": 0.0,
      "Au|Cu": -9.0,
      "Au|Dy": -74.0,
      "Au|Er": -74.0,
      "Au|Fe": 8.0,
      "Au|Ga": -19.0,
      "Au|Gd": -74.0,
      "Au|Ge": -21.5,
      "Au|Hf": -63.0,
      "Au|Ho": -72.0,
      "Au|In": -11.0,
      "Au|Ir": 13.0,
      "Au|La": -73.0,
      "Au|Li": -37.0,
      "Au|Lu": -75.0,
      "Au|Mg": -32.0,
      "Au|Mn": -11.0,
      "Au|Mo": 3.0,
      "Au|Nb": -32.0,
      "Au|Nd": -73.0,
      "Au|Ni": 7.0,
      "Au|Os": 18.0,
      "Au|Pb": 2.0,
      "Au|Pd": 0.0,
      "Au|Pr": -73.0,
      "Au|Pt": 4.0,
      "Au|Re": 20.0,
      "Au|Rh": 7.0,
      "Au|Ru": 15.0,
      "Au|Sb": -4.0,
      "Au|Sc": -74.0,
      "Au|Si": -30.0,
      "Au|Sm": -74.0,
      "Au|Sn": -10.0,
      "Au|Sr": -59.0,
      "Au|Ta": -32.0,
      "Au|Tb": -74.0,
      "Au|Th": -78.0,
      "Au|Ti": -47.0,
      "Au|Tm": -74.0,
      "Au|U": -45.0,
      "Au|V": -19.0,
      "Au|W": 12.0,
      "Au|Y": -74.0,
      "Au|Yb": -59.0,
      "Au|Zn": -16.0,
      "Au|Zr": -74.0,
      "Be|Bi": 26.0,
      "Be|Ca": -14.0,
      "Be|Ce": -30.0,
      "Be|Co": -4.0,
      "Be|Cr": -7.0,
      "Be|Cu": 0.0,
      "Be|Dy": -32.0,
      "Be|Er": -33.0,
      "Be|Fe": -4.0,
      "Be|Ga": 5.0,
      "Be|Gd": -32.0,
      "Be|Ge": -3.5,
      "Be|Hf": -37.0,
      "Be|Ho": -32.0,
      "Be|In": 16.0,
      "Be|Ir": -5.0,
      "Be|La": -29.0,
      "Be|Li": -5.0,
      "Be|Lu": -35.0,
      "Be|Mg": -3.0,
      "Be|Mn": -10.0,
      "Be|Mo": -7.0,
      "Be|Nb": -25.0,
      "Be|Nd": -31.0,
      "Be|Ni": -4.0,
      "Be|Os": -2.0,
      "Be|Pb": 25.0,
      "Be|Pd": -8.0,
      "Be|Pr": -31.0,
      "Be|Pt": -10.0,
      "Be|Re": 0.0,
      "Be|Rh": -6.0,
      "Be|Ru": -3.0,
      "Be|Sb": 18.0,
      "Be|Sc": -36.0,
      "Be|Si": -15.0,
      "Be|Sm": -32.0,
      "Be|Sn": 15.0,
      "Be|Sr": -10.0,
      "Be|Ta": -24.0,
      "Be|Tb": -33.0,
      "Be|Th": -37.0,
      "Be|Ti": -30.0,
      "Be|Tm": -33.0,
      "Be|U": -25.0,
      "Be|V": -16.0,
      "Be|W": -3.0,
      "Be|Y": -32.0,
      "Be|Yb": -14.0,
      "Be|Zn": 4.0,
      "Be|Zr": -43.0,
      "Bi|Ca": -56.0,
      "Bi|Ce": -57.0,
      "Bi|Co": 14.0,
      "Bi|Cr": 24.0,
      "Bi|Cu": 15.0,
      "Bi|Dy": -53.0,
      "Bi|Er": -52.0,
      "Bi|Fe": 26.0,
      "Bi|Ga": 4.0,
      "Bi|Gd": -54.0,
      "Bi|Ge": -7.5,
      "Bi|Hf": -30.0,
      "Bi|Ho": -52.0,
      "Bi|In": -1.0,
      "Bi|Ir": 14.0,
      "Bi|La": -58.0,
      "Bi|Li": -23.0,
      "Bi|Lu": -51.0,
      "Bi|Mg": -10.0,
      "Bi|Mn": 3.0,
      "Bi|Mo": 38.0,
      "Bi|Nb": 12.0,
      "Bi|Nd": -55.0,
      "Bi|Ni": 10.0,
      "Bi|Os": 29.0,
      "Bi|Pb": 0.0,
      "Bi|Pd": -21.0,
      "Bi|Pr": -56.0,
      "Bi|Pt": -8.0,
      "Bi|Re": 40.0,
      "Bi|Rh": 3.0,
      "Bi|Ru": 23.0,
      "Bi|Sb": 1.0,
      "Bi|Sc": -46.0,
      "Bi|Si": -2.0,
      "Bi|Sm": -54.0,
      "Bi|Sn": 1.0,
      "Bi|Sr": -61.0,
      "Bi|Ta": 9.0,
      "Bi|Tb": -53.0,
      "Bi|Th": -48.0,
      "Bi|Ti": -14.0,
      "Bi|Tm": -51.0,
      "Bi|U": -26.0,
      "Bi|V": 10.0,
      "Bi|W": 45.0,
      "Bi|Y": -54.0,
      "Bi|Yb": -55.0,
      "Bi|Zn": 4.0,
      "Bi|Zr": -40.0,
      "Ca|Ce": 9.0,
      "Ca|Co": 2.0,
      "Ca|Cr": 38.0,
      "Ca|Cu": -13.0,
      "Ca|Dy": 12.0,
      "Ca|Er": 13.0,
      "Ca|Fe": 25.0,
      "Ca|Ga": -28.0,
      "Ca|Gd": 11.0,
      "Ca|Ge": -59.5,
      "Ca|Hf": 39.0,
      "Ca|Ho": 11.0,
      "Ca|In": -35.0,
      "Ca|Ir": -23.0,
      "Ca|La": 8.0,
      "Ca|Li": -1.0,
      "Ca|Lu": 14.0,
      "Ca|Mg": -6.0,
      "Ca|Mn": 19.0,
      "Ca|Mo": 56.0,
      "Ca|Nb": 63.0,
      "Ca|Nd": 10.0,
      "Ca|Ni": -7.0,
      "Ca|Os": 4.0,
      "Ca|Pb": -52.0,
      "Ca|Pd": -63.0,
      "Ca|Pr": 10.0,
      "Ca|Pt": -55.0,
      "Ca|Re": 28.0,
      "Ca|Rh": -28.0,
      "Ca|Ru": -4.0,
      "Ca|Sb": -62.0,
      "Ca|Sc": 17.0,
      "Ca|Si": -51.0,
      "Ca|Sm": 11.0,
      "Ca|Sn": -45.0,
      "Ca|Sr": 1.0,
      "Ca|Ta": 60.0,
      "Ca|Tb": 12.0,
      "Ca|Th": 19.0,
      "Ca|Ti": 43.0,
      "Ca|Tm": 13.0,
      "Ca|U": 24.0,
      "Ca|V": 44.0,
      "Ca|W": 57.0,
      "Ca|Y": 11.0,
      "Ca|Yb": 0.0,
      "Ca|Zn": -22.0,
      "Ca|Zr": 37.0,
      "Ce|Co": -18.0,
      "Ce|Cr": 15.0,
      "Ce|Cu": -21.0,
      "Ce|Dy": 0.0,
      "Ce|Er": 0.0,
      "Ce|Fe": 3.0,
      "Ce|Ga": -41.0,
      "Ce|Gd": 0.0,
      "Ce|Ge": -73.5,
      "Ce|Hf": 14.0,
      "Ce|Ho": 0.0,
      "Ce|In": -38.0,
      "Ce|Ir": -50.0,
      "Ce|La": 0.0,
      "Ce|Li": 7.0,
      "Ce|Lu": 1.0,
      "Ce|Mg": -7.0,
      "Ce|Mn": 1.0,
      "Ce|Mo": 29.0,
      "Ce|Nb": 34.0,
      "Ce|Nd": 0.0,
      "Ce|Ni": -28.0,
      "Ce|Os": -24.0,
      "Ce|Pb": -50.0,
      "Ce|Pd": -83.0,
      "Ce|Pr": 0.0,
      "Ce|Pt": -81.0,
      "Ce|Re": 0.0,
      "Ce|Rh": -52.0,
      "Ce|Ru": -30.0,
      "Ce|Sb": -70.0,
      "Ce|Sc": 2.0,
      "Ce|Si": -73.0,
      "Ce|Sm": 0.0,
      "Ce|Sn": -52.0,
      "Ce|Sr": 15.0,
      "Ce|Ta": 31.0,
      "Ce|Tb": 0.0,
      "Ce|Th": 2.0,
      "Ce|Ti": 18.0,
      "Ce|Tm": 0.0,
      "Ce|U": 6.0,
      "Ce|V": 20.0,
      "Ce|W": 29.0,
      "Ce|Y": 0.0,
      "Ce|Yb": 8.0,
      "Ce|Zn": -31.0,
      "Ce|Zr": 12.0,
      "Co|Cr": -4.0,
      "Co|Cu": 6.0,
      "Co|Dy": -23.0,
      "Co|Er": -24.0,
      "Co|Fe": -1.0,
      "Co|Ga": -11.0,
      "Co|Gd": -22.0,
      "Co|Ge": -21.5,
      "Co|Hf": -35.0,
      "Co|Ho": -22.0,
      "Co|In": 7.0,
      "Co|Ir": -3.0,
      "Co|La": -17.0,
      "Co|Li": 8.0,
      "Co|Lu": -27.0,
      "Co|Mg": 3.0,
      "Co|Mn": -5.0,
      "Co|Mo": -5.0,
      "Co|Nb": -25.0,
      "Co|Nd": -20.0,
      "Co|Ni": 0.0,
      "Co|Os": 0.0,
      "Co|Pb": 17.0,
      "Co|Pd": -1.0,
      "Co|Pr": -20.0,
      "Co|Pt": -7.0,
      "Co|Re": 2.0,
      "Co|Rh": -2.0,
      "Co|Ru": -1.0,
      "Co|Sb": 2.0,
      "Co|Sc": -30.0,
      "Co|Si": -38.0,
      "Co|Sm": -22.0,
      "Co|Sn": 0.0,
      "Co|Sr": 10.0,
      "Co|Ta": -24.0,
      "Co|Tb": -23.0,
      "Co|Th": -30.0,
      "Co|Ti": -28.0,
      "Co|Tm": -24.0,
      "Co|U": -19.0,
      "Co|V": -14.0,
      "Co|W": -1.0,
      "Co|Y": -22.0,
      "Co|Yb": 2.0,
      "Co|Zn": -5.0,
      "Co|Zr": -41.0,
      "Cr|Cu": 12.0,
      "Cr|Dy": 9.0,
      "Cr|Er": 8.0,
      "Cr|Fe": -1.0,
      "Cr|Ga": -1.0,
      "Cr|Gd": 11.0,
      "Cr|Ge": -18.5,
      "Cr|Hf": -9.0,
      "Cr|Ho": 10.0,
      "Cr|In": 20.0,
      "Cr|Ir": -18.0,
      "Cr|La": 17.0,
      "Cr|Li": 35.0,
      "Cr|Lu": 5.0,
      "Cr|Mg": 24.0,
      "Cr|Mn": 2.0,
      "Cr|Mo": 0.0,
      "Cr|Nb": -7.0,
      "Cr|Nd": 13.0,
      "Cr|Ni": -7.0,
      "Cr|Os": -11.0,
      "Cr|Pb": 28.0,
      "Cr|Pd": -15.0,
      "Cr|Pr": 13.0,
      "Cr|Pt": -24.0,
      "Cr|Re": -4.0,
      "Cr|Rh": -13.0,
      "Cr|Ru": -12.0,
      "Cr|Sb": 7.0,
      "Cr|Sc": 1.0,
      "Cr|Si": -37.0,
      "Cr|Sm": 11.0,
      "Cr|Sn": 10.0,
      "Cr|Sr": 47.0,
      "Cr|Ta": -7.0,
      "Cr|Tb": 9.0,
      "Cr|Th": 2.0,
      "Cr|Ti": -7.0,
      "Cr|Tm": 8.0,
      "Cr|U": 2.0,
      "Cr|V": -2.0,
      "Cr|W": 1.0,
      "Cr|Y": 11.0,
      "Cr|Yb": 37.0,
      "Cr|Zn": 5.0,
      "Cr|Zr": -12.0,
      "Cu|Dy": -22.0,
      "Cu|Er": -23.0,
      "Cu|Fe": 13.0,
      "Cu|Ga": 1.0,
      "Cu|Gd": -22.0,
      "Cu|Ge": -11.5,
      "Cu|Hf": -17.0,
      "Cu|Ho": -22.0,
      "Cu|In": 10.0,
      "Cu|Ir": 0.0,
      "Cu|La": -21.0,
      "Cu|Li": -5.0,
      "Cu|Lu": -24.0,
      "Cu|Mg": -3.0,
      "Cu|Mn": 4.0,
      "Cu|Mo": 19.0,
      "Cu|Nb": 3.0,
      "Cu|Nd": -22.0,
      "Cu|Ni": 4.0,
      "Cu|Os": 10.0,
      "Cu|Pb": 15.0,
      "Cu|Pd": -14.0,
      "Cu|Pr": -22.0,
      "Cu|Pt": -12.0,
      "Cu|Re": 18.0,
      "Cu|Rh": -2.0,
      "Cu|Ru": 7.0,
      "Cu|Sb": 7.0,
      "Cu|Sc": -24.0,
      "Cu|Si": -19.0,
      "Cu|Sm": -22.0,
      "Cu|Sn": 7.0,
      "Cu|Sr": -9.0,
      "Cu|Ta": 2.0,
      "Cu|Tb": -23.0,
      "Cu|Th": -24.0,
      "Cu|Ti": -9.0,
      "Cu|Tm": -23.0,
      "Cu|U": -9.0,
      "Cu|V": 5.0,
      "Cu|W": 22.0,
      "Cu|Y": -22.0,
      "Cu|Yb": -12.0,
      "Cu|Zn": 1.0,
      "Cu|Zr": -23.0,
      "Dy|Er": 0.0,
      "Dy|Fe": -3.0,
      "Dy|Ga": -40.0,
      "Dy|Gd": 0.0,
      "Dy|Ge": -71.5,
      "Dy|Hf": 10.0,
      "Dy|Ho": 0.0,
      "Dy|In": -35.0,
      "Dy|Ir": -55.0,
      "Dy|La": 0.0,
      "Dy|Li": 9.0,
      "Dy|Lu": 0.0,
      "Dy|Mg": -6.0,
      "Dy|Mn": -3.0,
      "Dy|Mo": 22.0,
      "Dy|Nb": 27.0,
      "Dy|Nd": 0.0,
      "Dy|Ni": -32.0,
      "Dy|Os": -29.0,
      "Dy|Pb": -46.0,
      "Dy|Pd": -84.0,
      "Dy|Pr": 0.0,
      "Dy|Pt": -84.0,
      "Dy|Re": -7.0,
      "Dy|Rh": -55.0,
      "Dy|Ru": -35.0,
      "Dy|Sb": -67.0,
      "Dy|Sc": 1.0,
      "Dy|Si": -74.0,
      "Dy|Sm": 0.0,
      "Dy|Sn": -50.0,
      "Dy|Sr": 18.0,
      "Dy|Ta": 25.0,
      "Dy|Tb": 0.0,
      "Dy|Th": 1.0,
      "Dy|Ti": 14.0,
      "Dy|Tm": 0.0,
      "Dy|U": 3.0,
      "Dy|V": 15.0,
      "Dy|W": 21.0,
      "Dy|Y": 0.0,
      "Dy|Yb": 11.0,
      "Dy|Zn": -31.0,
      "Dy|Zr": 8.0,
      "Er|Fe": -5.0,
      "Er|Ga": -40.0,
      "Er|Gd": 0.0,
      "Er|Ge": -71.5,
      "Er|Hf": 9.0,
      "Er|Ho": 0.0,
      "Er|In": -34.0,
      "Er|Ir": -56.0,
      "Er|La": 1.0,
      "Er|Li": 9.0,
      "Er|Lu": 0.0,
      "Er|Mg": -5.0,
      "Er|Mn": -4.0,
      "Er|Mo": 20.0,
      "Er|Nb": 26.0,
      "Er|Nd": 0.0,
      "Er|Ni": -34.0,
      "Er|Os": -31.0,
      "Er|Pb": -45.0,
      "Er|Pd": -85.0,
      "Er|Pr": 0.0,
      "Er|Pt": -86.0,
      "Er|Re": -9.0,
      "Er|Rh": -57.0,
      "Er|Ru": -37.0,
      "Er|Sb": -66.0,
      "Er|Sc": 0.0,
      "Er|Si": -74.0,
      "Er|Sm": 0.0,
      "Er|Sn": -49.0,
      "Er|Sr": 20.0,
      "Er|Ta": 23.0,
      "Er|Tb": 0.0,
      "Er|Th": 1.0,
      "Er|Ti": 13.0,
      "Er|Tm": 0.0,
      "Er|U": 2.0,
      "Er|V": 14.0,
      "Er|W": 19.0,
      "Er|Y": 0.0,
      "Er|Yb": 12.0,
      "Er|Zn": -31.0,
      "Er|Zr": 7.0,
      "Fe|Ga": -2.0,
      "Fe|Gd": -1.0,
      "Fe|Ge": -15.5,
      "Fe|Hf": -21.0,
      "Fe|Ho": -2.0,
      "Fe|In": 19.0,
      "Fe|Ir": -9.0,
      "Fe|La": 5.0,
      "Fe|Li": 26.0,
      "Fe|Lu": -7.0,
      "Fe|Mg": 18.0,
      "Fe|Mn": 0.0,
      "Fe|Mo": -2.0,
      "Fe|Nb": -16.0,
      "Fe|Nd": 1.0,
      "Fe|Ni": -2.0,
      "Fe|Os": -4.0,
      "Fe|Pb": 29.0,
      "Fe|Pd": -4.0,
      "Fe|Pr": 1.0,
      "Fe|Pt": -13.0,
      "Fe|Re": 0.0,
      "Fe|Rh": -5.0,
      "Fe|Ru": -5.0,
      "Fe|Sb": 10.0,
      "Fe|Sc": -11.0,
      "Fe|Si": -35.0,
      "Fe|Sm": -1.0,
      "Fe|Sn": 11.0,
      "Fe|Sr": 34.0,
      "Fe|Ta": -15.0,
      "Fe|Tb": -3.0,
      "Fe|Th": -11.0,
      "Fe|Ti": -17.0,
      "Fe|Tm": -5.0,
      "Fe|U": -6.0,
      "Fe|V": -7.0,
      "Fe|W": 0.0,
      "Fe|Y": -1.0,
      "Fe|Yb": 25.0,
      "Fe|Zn": 4.0,
      "Fe|Zr": -25.0,
      "Ga|Gd": -40.0,
      "Ga|Ge": -15.5,
      "Ga|Hf": -34.0,
      "Ga|Ho": -39.0,
      "Ga|In": 3.0,
      "Ga|Ir": -21.0,
      "Ga|La": -41.0,
      "Ga|Li": -9.0,
      "Ga|Lu": -40.0,
      "Ga|Mg": -4.0,
      "Ga|Mn": -13.0,
      "Ga|Mo": 7.0,
      "Ga|Nb": -8.0,
      "Ga|Nd": -40.0,
      "Ga|Ni": -15.0,
      "Ga|Os": -7.0,
      "Ga|Pb": 5.0,
      "Ga|Pd": -42.0,
      "Ga|Pr": -41.0,
      "Ga|Pt": -38.0,
      "Ga|Re": 3.0,
      "Ga|Rh": -25.0,
      "Ga|Ru": -11.0,
      "Ga|Sb": -1.0,
      "Ga|Sc": -38.0,
      "Ga|Si": -17.0,
      "Ga|Sm": -40.0,
      "Ga|Sn": 1.0,
      "Ga|Sr": -27.0,
      "Ga|Ta": -10.0,
      "Ga|Tb": -40.0,
      "Ga|Th": -39.0,
      "Ga|Ti": -23.0,
      "Ga|Tm": -39.0,
      "Ga|U": -29.0,
      "Ga|V": -8.0,
      "Ga|W": 11.0,
      "Ga|Y": -40.0,
      "Ga|Yb": -27.0,
      "Ga|Zn": 0.0,
      "Ga|Zr": -40.0,
      "Gd|Ge": -72.5,
      "Gd|Hf": 11.0,
      "Gd|Ho": 0.0,
      "Gd|In": -36.0,
      "Gd|Ir": -53.0,
      "Gd|La": 0.0,
      "Gd|Li": 8.0,
      "Gd|Lu": 0.0,
      "Gd|Mg": -6.0,
      "Gd|Mn": -1.0,
      "Gd|Mo": 24.0,
      "Gd|Nb": 30.0,
      "Gd|Nd": 0.0,
      "Gd|Ni": -31.0,
      "Gd|Os": -28.0,
      "Gd|Pb": -48.0,
      "Gd|Pd": -84.0,
      "Gd|Pr": 0.0,
      "Gd|Pt": -83.0,
      "Gd|Re": -4.0,
      "Gd|Rh": -54.0,
      "Gd|Ru": -34.0,
      "Gd|Sb": -68.0,
      "Gd|Sc": 1.0,
      "Gd|Si": -73.0,
      "Gd|Sm": 0.0,
      "Gd|Sn": -51.0,
      "Gd|Sr": 17.0,
      "Gd|Ta": 27.0,
      "Gd|Tb": 0.0,
      "Gd|Th": 1.0,
      "Gd|Ti": 15.0,
      "Gd|Tm": 0.0,
      "Gd|U": 4.0,
      "Gd|V": 17.0,
      "Gd|W": 24.0,
      "Gd|Y": 0.0,
      "Gd|Yb": 10.0,
      "Gd|Zn": -31.0,
      "Gd|Zr": 9.0,
      "Ge|Hf": -65.5,
      "Ge|Ho": -71.5,
      "Ge|In": -13.5,
      "Ge|Ir": -24.5,
      "Ge|La": -73.5,
      "Ge|Li": -34.5,
      "Ge|Lu": -71.5,
      "Ge|Mg": -26.5,
      "Ge|Mn": -31.5,
      "Ge|Mo": -13.5,
      "Ge|Nb": -36.5,
      "Ge|Nd": -101.5,
      "Ge|Ni": -23.5,
      "Ge|Os": -14.5,
      "Ge|Pb": -7.5,
      "Ge|Pd": -43.5,
      "Ge|Pr": -72.5,
      "Ge|Pt": -37.5,
      "Ge|Re": -7.5,
      "Ge|Rh": -29.5,
      "Ge|Ru": -18.5,
      "Ge|Sb": -10.5,
      "Ge|Sc": -69.5,
      "Ge|Si": -14.5,
      "Ge|Sm": -72.5,
      "Ge|Sn": -12.5,
      "Ge|Sr": -59.5,
      "Ge|Ta": -37.5,
      "Ge|Tb": -72.5,
      "Ge|Th": -72.5,
      "Ge|Ti": -51.5,
      "Ge|Tm": -71.5,
      "Ge|U": -56.5,
      "Ge|V": -31.5,
      "Ge|W": -7.5,
      "Ge|Y": -72.5,
      "Ge|Yb": -58.5,
      "Ge|Zn": -15.5,
      "Ge|Zr": -72.5,
      "Hf|Ho": 10.0,
      "Hf|In": -18.0,
      "Hf|Ir": -68.0,
      "Hf|La": 15.0,
      "Hf|Li": 30.0,
      "Hf|Lu": 8.0,
      "Hf|Mg": 10.0,
      "Hf|Mn": -12.0,
      "Hf|Mo": -4.0,
      "Hf|Nb": 4.0,
      "Hf|Nd": 13.0,
      "Hf|Ni": -42.0,
      "Hf|Os": -48.0,
      "Hf|Pb": -23.0,
      "Hf|Pd": -80.0,
      "Hf|Pr": 13.0,
      "Hf|Pt": -90.0,
      "Hf|Re": -30.0,
      "Hf|Rh": -63.0,
      "Hf|Ru": -52.0,
      "Hf|Sb": -50.0,
      "Hf|Sc": 5.0,
      "Hf|Si": -77.0,
      "Hf|Sm": 11.0,
      "Hf|Sn": -35.0,
      "Hf|Sr": 50.0,
      "Hf|Ta": 3.0,
      "Hf|Tb": 10.0,
      "Hf|Th": 6.0,
      "Hf|Ti": 0.0,
      "Hf|Tm": 9.0,
      "Hf|U": -1.0,
      "Hf|V": -2.0,
      "Hf|W": -6.0,
      "Hf|Y": 11.0,
      "Hf|Yb": 38.0,
      "Hf|Zn": -24.0,
      "Hf|Zr": 0.0,
      "Ho|In": -35.0,
      "Ho|Ir": -53.0,
      "Ho|La": 0.0,
      "Ho|Li": 8.0,
      "Ho|Lu": 0.0,
      "Ho|Mg": -6.0,
      "Ho|Mn": -2.0,
      "Ho|Mo": 22.0,
      "Ho|Nb": 28.0,
      "Ho|Nd": 0.0,
      "Ho|Ni": -31.0,
      "Ho|Os": -28.0,
      "Ho|Pb": -46.0,
      "Ho|Pd": -83.0,
      "Ho|Pr": 0.0,
      "Ho|Pt": -83.0,
      "Ho|Re": -5.0,
      "Ho|Rh": -54.0,
      "Ho|Ru": -34.0,
      "Ho|Sb": -66.0,
      "Ho|Sc": 1.0,
      "Ho|Si": -73.0,
      "Ho|Sm": 0.0,
      "Ho|Sn": -49.0,
      "Ho|Sr": 18.0,
      "Ho|Ta": 26.0,
      "Ho|Tb": 0.0,
      "Ho|Th": 1.0,
      "Ho|Ti": 14.0,
      "Ho|Tm": 0.0,
      "Ho|U": 3.0,
      "Ho|V": 16.0,
      "Ho|W": 22.0,
      "Ho|Y": 0.0,
      "Ho|Yb": 11.0,
      "Ho|Zn": -30.0,
      "Ho|Zr": 9.0,
      "In|Ir": 0.0,
      "In|La": -39.0,
      "In|Li": -12.0,
      "In|Lu": -34.0,
      "In|Mg": -4.0,
      "In|Mn": 3.0,
      "In|Mo": 33.0,
      "In|Nb": 15.0,
      "In|Nd": -37.0,
      "In|Ni": 2.0,
      "In|Os": 16.0,
      "In|Pb": -1.0,
      "In|Pd": -31.0,
      "In|Pr": -37.0,
      "In|Pt": -21.0,
      "In|Re": 29.0,
      "In|Rh": -8.0,
      "In|Ru": 10.0,
      "In|Sb": -4.0,
      "In|Sc": -30.0,
      "In|Si": -10.0,
      "In|Sm": -36.0,
      "In|Sn": 0.0,
      "In|Sr": -37.0,
      "In|Ta": 13.0,
      "In|Tb": -35.0,
      "In|Th": -31.0,
      "In|Ti": -5.0,
      "In|Tm": -34.0,
      "In|U": -16.0,
      "In|V": 12.0,
      "In|W": 38.0,
      "In|Y": -36.0,
      "In|Yb": -34.0,
      "In|Zn": 3.0,
      "In|Zr": -25.0,
      "Ir|La": -48.0,
      "Ir|Li": -9.0,
      "Ir|Lu": -59.0,
      "Ir|Mg": -13.0,
      "Ir|Mn": -18.0,
      "Ir|Mo": -21.0,
      "Ir|Nb": -53.0,
      "Ir|Nd": -51.0,
      "Ir|Ni": -2.0,
      "Ir|Os": -1.0,
      "Ir|Pb": 16.0,
      "Ir|Pd": 6.0,
      "Ir|Pr": -52.0,
      "Ir|Pt": 0.0,
      "Ir|Re": -3.0,
      "Ir|Rh": 1.0,
      "Ir|Ru": -1.0,
      "Ir|Sb": 1.0,
      "Ir|Sc": -62.0,
      "Ir|Si": -43.0,
      "Ir|Sm": -53.0,
      "Ir|Sn": -5.0,
      "Ir|Sr": -16.0,
      "Ir|Ta": -52.0,
      "Ir|Tb": -55.0,
      "Ir|Th": -64.0,
      "Ir|Ti": -57.0,
      "Ir|Tm": -56.0,
      "Ir|U": -44.0,
      "Ir|V": -34.0,
      "Ir|W": -16.0,
      "Ir|Y": -53.0,
      "Ir|Yb": -22.0,
      "Ir|Zn": -13.0,
      "Ir|Zr": -76.0,
      "La|Li": 6.0,
      "La|Lu": 1.0,
      "La|Mg": -7.0,
      "La|Mn": 3.0,
      "La|Mo": 31.0,
      "La|Nb": 36.0,
      "La|Nd": 0.0,
      "La|Ni": -27.0,
      "La|Os": -21.0,
      "La|Pb": -51.0,
      "La|Pd": -82.0,
      "La|Pr": 0.0,
      "La|Pt": -80.0,
      "La|Re": 3.0,
      "La|Rh": -50.0,
      "La|Ru": -28.0,
      "La|Sb": -71.0,
      "La|Sc": 2.0,
      "La|Si": -73.0,
      "La|Sm": 0.0,
      "La|Sn": -53.0,
      "La|Sr": 14.0,
      "La|Ta": 33.0,
      "La|Tb": 0.0,
      "La|Th": 3.0,
      "La|Ti": 20.0,
      "La|Tm": 1.0,
      "La|U": 7.0,
      "La|V": 22.0,
      "La|W": 32.0,
      "La|Y": 0.0,
      "La|Yb": 8.0,
      "La|Zn": -31.0,
      "La|Zr": 13.0,
      "Li|Lu": 10.0,
      "Li|Mg": 0.0,
      "Li|Mn": 19.0,
      "Li|Mo": 49.0,
      "Li|Nb": 51.0,
      "Li|Nd": 7.0,
      "Li|Ni": 1.0,
      "Li|Os": 11.0,
      "Li|Pb": -21.0,
      "Li|Pd": -40.0,
      "Li|Pr": 7.0,
      "Li|Pt": -33.0,
      "Li|Re": 29.0,
      "Li|Rh": -14.0,
      "Li|Ru": 5.0,
      "Li|Sb": -28.0,
      "Li|Sc": 12.0,
      "Li|Si": -30.0,
      "Li|Sm": 8.0,
      "Li|Sn": -18.0,
      "Li|Sr": 0.0,
      "Li|Ta": 48.0,
      "Li|Tb": 9.0,
      "Li|Th": 14.0,
      "Li|Ti": 34.0,
      "Li|Tm": 9.0,
      "Li|U": 21.0,
      "Li|V": 37.0,
      "Li|W": 50.0,
      "Li|Y": 8.0,
      "Li|Yb": -1.0,
      "Li|Zn": -7.0,
      "Li|Zr": 27.0,
      "Lu|Mg": -5.0,
      "Lu|Mn": -6.0,
      "Lu|Mo": 17.0,
      "Lu|Nb": 23.0,
      "Lu|Nd": 0.0,
      "Lu|Ni": -36.0,
      "Lu|Os": -34.0,
      "Lu|Pb": -45.0,
      "Lu|Pd": -87.0,
      "Lu|Pr": 0.0,
      "Lu|Pt": -88.0,
      "Lu|Re": -12.0,
      "Lu|Rh": -59.0,
      "Lu|Ru": -40.0,
      "Lu|Sb": -66.0,
      "Lu|Sc": 0.0,
      "Lu|Si": -75.0,
      "Lu|Sm": 0.0,
      "Lu|Sn": -49.0,
      "Lu|Sr": 21.0,
      "Lu|Ta": 21.0,
      "Lu|Tb": 0.0,
      "Lu|Th": 0.0,
      "Lu|Ti": 11.0,
      "Lu|Tm": 0.0,
      "Lu|U": 1.0,
      "Lu|V": 11.0,
      "Lu|W": 16.0,
      "Lu|Y": 0.0,
      "Lu|Yb": 14.0,
      "Lu|Zn": -31.0,
      "Lu|Zr": 6.0,
      "Mg|Mn": 10.0,
      "Mg|Mo": 36.0,
      "Mg|Nb": 32.0,
      "Mg|Nd": -6.0,
      "Mg|Ni": -4.0,
      "Mg|Os": 5.0,
      "Mg|Pb": -8.0,
      "Mg|Pd": -40.0,
      "Mg|Pr": -6.0,
      "Mg|Pt": -35.0,
      "Mg|Re": 21.0,
      "Mg|Rh": -17.0,
      "Mg|Ru": 0.0,
      "Mg|Sb": -16.0,
      "Mg|Sc": -3.0,
      "Mg|Si": -26.0,
      "Mg|Sm": -6.0,
      "Mg|Sn": -9.0,
      "Mg|Sr": -4.0,
      "Mg|Ta": 30.0,
      "Mg|Tb": -6.0,
      "Mg|Th": -3.0,
      "Mg|Ti": 16.0,
      "Mg|Tm": -5.0,
      "Mg|U": 6.0,
      "Mg|V": 23.0,
      "Mg|W": 38.0,
      "Mg|Y": -6.0,
      "Mg|Yb": -6.0,
      "Mg|Zn": -4.0,
      "Mg|Zr": 6.0,
      "Mn|Mo": 5.0,
      "Mn|Nb": -4.0,
      "Mn|Nd": 0.0,
      "Mn|Ni": -8.0,
      "Mn|Os": -9.0,
      "Mn|Pb": 7.0,
      "Mn|Pd": -23.0,
      "Mn|Pr": 0.0,
      "Mn|Pt": -28.0,
      "Mn|Re": -1.0,
      "Mn|Rh": -16.0,
      "Mn|Ru": -11.0,
      "Mn|Sb": -11.0,
      "Mn|Sc": -8.0,
      "Mn|Si": -45.0,
      "Mn|Sm": -1.0,
      "Mn|Sn": -7.0,
      "Mn|Sr": 27.0,
      "Mn|Ta": -4.0,
      "Mn|Tb": -3.0,
      "Mn|Th": -8.0,
      "Mn|Ti": -8.0,
      "Mn|Tm": -4.0,
      "Mn|U": -4.0,
      "Mn|V": -1.0,
      "Mn|W": 6.0,
      "Mn|Y": -1.0,
      "Mn|Yb": 19.0,
      "Mn|Zn": -6.0,
      "Mn|Zr": -15.0,
      "Mo|Nb": -6.0,
      "Mo|Nd": 26.0,
      "Mo|Ni": -7.0,
      "Mo|Os": -14.0,
      "Mo|Pb": 42.0,
      "Mo|Pd": -15.0,
      "Mo|Pr": 26.0,
      "Mo|Pt": -28.0,
      "Mo|Re": -7.0,
      "Mo|Rh": -15.0,
      "Mo|Ru": -14.0,
      "Mo|Sb": 17.0,
      "Mo|Sc": 11.0,
      "Mo|Si": -35.0,
      "Mo|Sm": 24.0,
      "Mo|Sn": 20.0,
      "Mo|Sr": 69.0,
      "Mo|Ta": -5.0,
      "Mo|Tb": 22.0,
      "Mo|Th": 13.0,
      "Mo|Ti": -4.0,
      "Mo|Tm": 19.0,
      "Mo|U": 8.0,
      "Mo|V": 0.0,
      "Mo|W": 0.0,
      "Mo|Y": 24.0,
      "Mo|Yb": 55.0,
      "Mo|Zn": 12.0,
      "Mo|Zr": -6.0,
      "Nb|Nd": 32.0,
      "Nb|Ni": -30.0,
      "Nb|Os": -39.0,
      "Nb|Pb": 17.0,
      "Nb|Pd": -53.0,
      "Nb|Pr": 32.0,
      "Nb|Pt": -67.0,
      "Nb|Re": -26.0,
      "Nb|Rh": -46.0,
      "Nb|Ru": -41.0,
      "Nb|Sb": -11.0,
      "Nb|Sc": 18.0,
      "Nb|Si": -56.0,
      "Nb|Sm": 30.0,
      "Nb|Sn": -1.0,
      "Nb|Sr": 76.0,
      "Nb|Ta": 0.0,
      "Nb|Tb": 28.0,
      "Nb|Th": 20.0,
      "Nb|Ti": 2.0,
      "Nb|Tm": 25.0,
      "Nb|U": 9.0,
      "Nb|V": -1.0,
      "Nb|W": -8.0,
      "Nb|Y": 30.0,
      "Nb|Yb": 61.0,
      "Nb|Zn": -1.0,
      "Nb|Zr": 4.0,
      "Nd|Ni": -30.0,
      "Nd|Os": -26.0,
      "Nd|Pb": -49.0,
      "Nd|Pd": -83.0,
      "Nd|Pr": 0.0,
      "Nd|Pt": -82.0,
      "Nd|Re": -2.0,
      "Nd|Rh": -53.0,
      "Nd|Ru": -32.0,
      "Nd|Sb": -69.0,
      "Nd|Sc": 2.0,
      "Nd|Si": -73.0,
      "Nd|Sm": 0.0,
      "Nd|Sn": -51.0,
      "Nd|Sr": 16.0,
      "Nd|Ta": 29.0,
      "Nd|Tb": 0.0,
      "Nd|Th": 2.0,
      "Nd|Ti": 17.0,
      "Nd|Tm": 0.0,
      "Nd|U": 5.0,
      "Nd|V": 18.0,
      "Nd|W": 26.0,
      "Nd|Y": 0.0,
      "Nd|Yb": 9.0,
      "Nd|Zn": -31.0,
      "Nd|Zr": 10.0,
      "Ni|Os": 1.0,
      "Ni|Pb": 13.0,
      "Ni|Pd": 0.0,
      "Ni|Pr": -30.0,
      "Ni|Pt": -5.0,
      "Ni|Re": 2.0,
      "Ni|Rh": -1.0,
      "Ni|Ru": 0.0,
      "Ni|Sb": -1.0,
      "Ni|Sc": -39.0,
      "Ni|Si": -40.0,
      "Ni|Sm": -31.0,
      "Ni|Sn": -4.0,
      "Ni|Sr": -1.0,
      "Ni|Ta": -29.0,
      "Ni|Tb": -32.0,
      "Ni|Th": -39.0,
      "Ni|Ti": -35.0,
      "Ni|Tm": -34.0,
      "Ni|U": -25.0,
      "Ni|V": -18.0,
      "Ni|W": -3.0,
      "Ni|Y": -31.0,
      "Ni|Yb": -7.0,
      "Ni|Zn": -9.0,
      "Ni|Zr": -49.0,
      "Os|Pb": 32.0,
      "Os|Pd": 8.0,
      "Os|Pr": -26.0,
      "Os|Pt": 0.0,
      "Os|Re": -1.0,
      "Os|Rh": 2.0,
      "Os|Ru": 0.0,
      "Os|Sb": 14.0,
      "Os|Sc": -39.0,
      "Os|Si": -36.0,
      "Os|Sm": -28.0,
      "Os|Sn": 9.0,
      "Os|Sr": 13.0,
      "Os|Ta": -38.0,
      "Os|Tb": -30.0,
      "Os|Th": -39.0,
      "Os|Ti": -41.0,
      "Os|Tm": -31.0,
      "Os|U": -26.0,
      "Os|V": -23.0,
      "Os|W": -10.0,
      "Os|Y": -28.0,
      "Os|Yb": 4.0,
      "Os|Zn": -1.0,
      "Os|Zr": -55.0,
      "Pb|Pd": -18.0,
      "Pb|Pr": -49.0,
      "Pb|Pt": -5.0,
      "Pb|Re": 44.0,
      "Pb|Rh": 6.0,
      "Pb|Ru": 25.0,
      "Pb|Sb": 1.0,
      "Pb|Sc": -40.0,
      "Pb|Si": -2.0,
      "Pb|Sm": -48.0,
      "Pb|Sn": 2.0,
      "Pb|Sr": -56.0,
      "Pb|Ta": 15.0,
      "Pb|Tb": -47.0,
      "Pb|Th": -41.0,
      "Pb|Ti": -8.0,
      "Pb|Tm": -45.0,
      "Pb|U": -20.0,
      "Pb|V": 15.0,
      "Pb|W": 49.0,
      "Pb|Y": -48.0,
      "Pb|Yb": -50.0,
      "Pb|Zn": 5.0,
      "Pb|Zr": -33.0,
      "Pd|Pr": -83.0,
      "Pd|Pt": 2.0,
      "Pd|Re": 6.0,
      "Pd|Rh": 2.0,
      "Pd|Ru": 6.0,
      "Pd|Sb": -28.0,
      "Pd|Sc": -86.0,
      "Pd|Si": -55.0,
      "Pd|Sm": -84.0,
      "Pd|Sn": -34.0,
      "Pd|Sr": -61.0,
      "Pd|Ta": -52.0,
      "Pd|Tb": -85.0,
      "Pd|Th": -91.0,
      "Pd|Ti": -65.0,
      "Pd|Tm": -85.0,
      "Pd|U": -58.0,
      "Pd|V": -35.0,
      "Pd|W": -6.0,
      "Pd|Y": -84.0,
      "Pd|Yb": -62.0,
      "Pd|Zn": -33.0,
      "Pd|Zr": -91.0,
      "Pr|Pt": -82.0,
      "Pr|Re": -2.0,
      "Pr|Rh": -53.0,
      "Pr|Ru": -32.0,
      "Pr|Sb": -69.0,
      "Pr|Sc": 1.0,
      "Pr|Si": -73.0,
      "Pr|Sm": 0.0,
      "Pr|Sn": -52.0,
      "Pr|Sr": 16.0,
      "Pr|Ta": 29.0,
      "Pr|Tb": 0.0,
      "Pr|Th": 2.0,
      "Pr|Ti": 17.0,
      "Pr|Tm": 0.0,
      "Pr|U": 5.0,
      "Pr|V": 18.0,
      "Pr|W": 26.0,
      "Pr|Y": 0.0,
      "Pr|Yb": 9.0,
      "Pr|Zn": -31.0,
      "Pr|Zr": 10.0,
      "Pt|Re": -4.0,
      "Pt|Rh": -2.0,
      "Pt|Ru": -1.0,
      "Pt|Sb": -17.0,
      "Pt|Sc": -89.0,
      "Pt|Si": -53.0,
      "Pt|Sm": -84.0,
      "Pt|Sn": -25.0,
      "Pt|Sr": -50.0,
      "Pt|Ta": -66.0,
      "Pt|Tb": -85.0,
      "Pt|Th": -94.0,
      "Pt|Ti": -74.0,
      "Pt|Tm": -85.0,
      "Pt|U": -63.0,
      "Pt|V": -45.0,
      "Pt|W": -20.0,
      "Pt|Y": -83.0,
      "Pt|Yb": -54.0,
      "Pt|Zn": -29.0,
      "Pt|Zr": -100.0,
      "Re|Rh": 1.0,
      "Re|Ru": -1.0,
      "Re|Sb": 23.0,
      "Re|Sc": -17.0,
      "Re|Si": -31.0,
      "Re|Sm": -4.0,
      "Re|Sn": 20.0,
      "Re|Sr": 39.0,
      "Re|Ta": -24.0,
      "Re|Tb": -7.0,
      "Re|Th": -16.0,
      "Re|Ti": -25.0,
      "Re|Tm": -9.0,
      "Re|U": -10.0,
      "Re|V": -13.0,
      "Re|W": -4.0,
      "Re|Y": -4.0,
      "Re|Yb": 28.0,
      "Re|Zn": 8.0,
      "Re|Zr": -35.0,
      "Rh|Ru": 1.0,
      "Rh|Sb": -8.0,
      "Rh|Sc": -61.0,
      "Rh|Si": -46.0,
      "Rh|Sm": -54.0,
      "Rh|Sn": -13.0,
      "Rh|Sr": -22.0,
      "Rh|Ta": -45.0,
      "Rh|Tb": -56.0,
      "Rh|Th": -63.0,
      "Rh|Ti": -52.0,
      "Rh|Tm": -56.0,
      "Rh|U": -42.0,
      "Rh|V": -29.0,
      "Rh|W": -9.0,
      "Rh|Y": -54.0,
      "Rh|Yb": -28.0,
      "Rh|Zn": -17.0,
      "Rh|Zr": -72.0,
      "Ru|Sb": 9.0,
      "Ru|Sc": -44.0,
      "Ru|Si": -38.0,
      "Ru|Sm": -34.0,
      "Ru|Sn": 4.0,
      "Ru|Sr": 5.0,
      "Ru|Ta": -39.0,
      "Ru|Tb": -35.0,
      "Ru|Th": -45.0,
      "Ru|Ti": -43.0,
      "Ru|Tm": -37.0,
      "Ru|U": -30.0,
      "Ru|V": -25.0,
      "Ru|W": -10.0,
      "Ru|Y": -34.0,
      "Ru|Yb": -4.0,
      "Ru|Zn": -5.0,
      "Ru|Zr": -59.0,
      "Sb|Sc": -61.0,
      "Sb|Si": -8.0,
      "Sb|Sm": -68.0,
      "Sb|Sn": -1.0,
      "Sb|Sr": -66.0,
      "Sb|Ta": -13.0,
      "Sb|Tb": -67.0,
      "Sb|Th": -65.0,
      "Sb|Ti": -33.0,
      "Sb|Tm": -66.0,
      "Sb|U": -42.0,
      "Sb|V": -8.0,
      "Sb|W": 25.0,
      "Sb|Y": -68.0,
      "Sb|Yb": -61.0,
      "Sb|Zn": -1.0,
      "Sb|Zr": -60.0,
      "Sc|Si": -74.0,
      "Sc|Sm": 1.0,
      "Sc|Sn": -45.0,
      "Sc|Sr": 25.0,
      "Sc|Ta": 16.0,
      "Sc|Tb": 1.0,
      "Sc|Th": 0.0,
      "Sc|Ti": 8.0,
      "Sc|Tm": 0.0,
      "Sc|U": -1.0,
      "Sc|V": 7.0,
      "Sc|W": 9.0,
      "Sc|Y": 1.0,
      "Sc|Yb": 16.0,
      "Sc|Zn": -29.0,
      "Sc|Zr": 4.0,
      "Si|Sm": -74.0,
      "Si|Sn": -11.0,
      "Si|Sr": -49.0,
      "Si|Ta": -56.0,
      "Si|Tb": -74.0,
      "Si|Th": -77.0,
      "Si|Ti": -66.0,
      "Si|Tm": -74.0,
      "Si|U": -66.0,
      "Si|V": -48.0,
      "Si|W": -31.0,
      "Si|Y": -73.0,
      "Si|Yb": -51.0,
      "Si|Zn": -18.0,
      "Si|Zr": -84.0,
      "Sm|Sn": -51.0,
      "Sm|Sr": 17.0,
      "Sm|Ta": 27.0,
      "Sm|Tb": 0.0,
      "Sm|Th": 1.0,
      "Sm|Ti": 15.0,
      "Sm|Tm": 0.0,
      "Sm|U": 4.0,
      "Sm|V": 17.0,
      "Sm|W": 24.0,
      "Sm|Y": 0.0,
      "Sm|Yb": 10.0,
      "Sm|Zn": -31.0,
      "Sm|Zr": 9.0,
      "Sn|Sr": -46.0,
      "Sn|Ta": -3.0,
      "Sn|Tb": -50.0,
      "Sn|Th": -48.0,
      "Sn|Ti": -21.0,
      "Sn|Tm": -49.0,
      "Sn|U": -30.0,
      "Sn|V": -1.0,
      "Sn|W": 27.0,
      "Sn|Y": -51.0,
      "Sn|Yb": -43.0,
      "Sn|Zn": 1.0,
      "Sn|Zr": -43.0,
      "Sr|Ta": 73.0,
      "Sr|Tb": 18.0,
      "Sr|Th": 27.0,
      "Sr|Ti": 53.0,
      "Sr|Tm": 20.0,
      "Sr|U": 33.0,
      "Sr|V": 54.0,
      "Sr|W": 70.0,
      "Sr|Y": 17.0,
      "Sr|Yb": 1.0,
      "Sr|Zn": -21.0,
      "Sr|Zr": 48.0,
      "Ta|Tb": 25.0,
      "Ta|Th": 18.0,
      "Ta|Ti": 1.0,
      "Ta|Tm": 23.0,
      "Ta|U": 8.0,
      "Ta|V": -1.0,
      "Ta|W": -7.0,
      "Ta|Y": 27.0,
      "Ta|Yb": 58.0,
      "Ta|Zn": -3.0,
      "Ta|Zr": 3.0,
      "Tb|Th": 1.0,
      "Tb|Ti": 14.0,
      "Tb|Tm": 0.0,
      "Tb|U": 3.0,
      "Tb|V": 15.0,
      "Tb|W": 21.0,
      "Tb|Y": 0.0,
      "Tb|Yb": 11.0,
      "Tb|Zn": -31.0,
      "Tb|Zr": 8.0,
      "Th|Ti": 8.0,
      "Th|Tm": 1.0,
      "Th|V": 9.0,
      "Th|W": 12.0,
      "Th|Y": 1.0,
      "Th|Yb": 18.0,
      "Th|Zn": -30.0,
      "Th|Zr": 4.0,
      "Ti|Tm": 12.0,
      "Ti|U": 2.0,
      "Ti|V": -2.0,
      "Ti|W": -6.0,
      "Ti|Y": 15.0,
      "Ti|Yb": 41.0,
      "Ti|Zn": -15.0,
      "Ti|Zr": 0.0,
      "Tm|U": 2.0,
      "Tm|V": 13.0,
      "Tm|W": 19.0,
      "Tm|Y": 0.0,
      "Tm|Yb": 12.0,
      "Tm|Zn": -30.0,
      "Tm|Zr": 7.0,
      "U|V": 4.0,
      "U|W": 8.0,
      "U|Y": 4.0,
      "U|Yb": 24.0,
      "U|Zn": -20.0,
      "U|Zr": -3.0,
      "V|W": -1.0,
      "V|Y": 17.0,
      "V|Yb": 43.0,
      "V|Zn": -2.0,
      "V|Zr": -4.0,
      "W|Y": 24.0,
      "W|Yb": 56.0,
      "W|Zn": 15.0,
      "W|Zr": -9.0,
      "Y|Yb": 10.0,
      "Y|Zn": -31.0,
      "Y|Zr": 9.0,
      "Yb|Zn": -21.0,
      "Yb|Zr": 36.0,
      "Zn|Zr": -29.0
    };

    // BEGIN GENERATED: ELEMENT_MECHANICS
    // Bulk modulus B (GPa) and molar volume Vm (cm3/mol) per element,
    // from the vendored matminer Miedema table (the upstream column
    // named 'compressibility' holds B in GPa). Feeds the Andreoli
    // elastic-strain energy. Generated by tests/data/_sync_js_tables.py.
    var ELEMENT_MECHANICS = {
      Ag: { B: 100.7, Vm: 10.25 },
      Al: { B: 72.18, Vm: 10.0 },
      Au: { B: 173.2, Vm: 10.2 },
      Be: { B: 100.4, Vm: 4.9 },
      Bi: { B: 31.48, Vm: 19.32 },
      Ca: { B: 15.21, Vm: 26.2 },
      Ce: { B: 23.95, Vm: 21.62 },
      Co: { B: 191.5, Vm: 6.7 },
      Cr: { B: 190.3, Vm: 7.23 },
      Cu: { B: 131.0, Vm: 7.12 },
      Dy: { B: 38.44, Vm: 19.0 },
      Er: { B: 41.08, Vm: 18.45 },
      Fe: { B: 168.3, Vm: 7.09 },
      Ga: { B: 56.9, Vm: 11.82 },
      Gd: { B: 38.34, Vm: 19.9 },
      Ge: { B: 77.24, Vm: 9.87 },
      Hf: { B: 108.9, Vm: 13.45 },
      Ho: { B: 39.68, Vm: 18.76 },
      In: { B: 41.09, Vm: 15.75 },
      Ir: { B: 355.1, Vm: 8.52 },
      La: { B: 24.3, Vm: 22.55 },
      Li: { B: 11.58, Vm: 13.0 },
      Lu: { B: 41.13, Vm: 17.77 },
      Mg: { B: 35.44, Vm: 14.0 },
      Mn: { B: 59.67, Vm: 7.35 },
      Mo: { B: 272.6, Vm: 9.4 },
      Nb: { B: 170.3, Vm: 10.87 },
      Nd: { B: 32.68, Vm: 20.58 },
      Ni: { B: 186.4, Vm: 6.6 },
      Os: { B: 417.9, Vm: 8.45 },
      Pb: { B: 42.99, Vm: 18.28 },
      Pd: { B: 180.9, Vm: 8.9 },
      Pr: { B: 30.58, Vm: 20.79 },
      Pt: { B: 278.4, Vm: 9.1 },
      Re: { B: 371.8, Vm: 8.85 },
      Rh: { B: 270.6, Vm: 8.3 },
      Ru: { B: 320.9, Vm: 8.2 },
      Sb: { B: 38.29, Vm: 16.95 },
      Sc: { B: 57.29, Vm: 15.03 },
      Si: { B: 98.88, Vm: 8.6 },
      Sm: { B: 29.41, Vm: 20.01 },
      Sn: { B: 110.9, Vm: 16.3 },
      Sr: { B: 11.62, Vm: 33.93 },
      Ta: { B: 200.1, Vm: 10.81 },
      Tb: { B: 39.93, Vm: 19.32 },
      Th: { B: 54.29, Vm: 19.8 },
      Ti: { B: 105.2, Vm: 10.58 },
      Tm: { B: 39.7, Vm: 18.12 },
      U: { B: 98.79, Vm: 13.15 },
      V: { B: 162.0, Vm: 8.36 },
      W: { B: 323.3, Vm: 9.55 },
      Y: { B: 36.62, Vm: 19.9 },
      Yb: { B: 13.27, Vm: 17.97 },
      Zn: { B: 59.85, Vm: 9.17 },
      Zr: { B: 83.335, Vm: 14.0 }
    };
    // END GENERATED: ELEMENT_MECHANICS

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

    function elementsMissingChi(norm, elementData) {
      var missing = [];
      var key;
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        if (!isFinite(elementData[key].chi)) {
          missing.push(key);
        }
      }
      return sortStrings(missing);
    }

    function meanChiFromNormalized(norm, elementData) {
      return sumByNorm(norm, elementData, "chi");
    }

    function deltaChiFromNormalized(norm, elementData) {
      var chiBar = meanChiFromNormalized(norm, elementData);
      var inner = 0.0;
      var key;
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        inner += norm[key] * Math.pow(elementData[key].chi - chiBar, 2);
      }
      return Math.sqrt(Math.max(inner, 0.0));
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

    function lambdaFromNormalized(norm, elementData) {
      // Singh 2014: Lambda = S_mix / delta^2, delta in percent.
      var d = deltaFromNormalized(norm, elementData);
      if (d === 0.0) {
        return Infinity;
      }
      return smixFromNormalized(norm) / (d * d);
    }

    function omegaSolidAngle(rCenter, rBar) {
      var s = rCenter + rBar;
      return 1.0 - Math.sqrt((s * s - rBar * rBar) / (s * s));
    }

    function gammaFromNormalized(norm, elementData) {
      // Wang 2015: gamma = omega_S / omega_L (tangent-cone solid angles).
      var rBar = sumByNorm(norm, elementData, "radius");
      var rMin = Infinity;
      var rMax = -Infinity;
      var key;
      var r;
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        r = elementData[key].radius;
        if (r < rMin) { rMin = r; }
        if (r > rMax) { rMax = r; }
      }
      return omegaSolidAngle(rMin, rBar) / omegaSolidAngle(rMax, rBar);
    }

    function hElasticFromNormalized(norm, mechanicsData) {
      // Andreoli 2019 Eqs. 9-10; B in GPa, V in cm3/mol -> kJ/mol.
      var table = mechanicsData || ELEMENT_MECHANICS;
      var weight = 0.0;
      var weighted = 0.0;
      var key;
      var entry;
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        entry = table[key];
        if (!entry || !(entry.B > 0) || !(entry.Vm > 0)) {
          return null;
        }
        weight += norm[key] * entry.B;
        weighted += norm[key] * entry.B * entry.Vm;
      }
      if (!(weight > 0)) {
        return null;
      }
      var vBar = weighted / weight;
      var total = 0.0;
      for (key in norm) {
        if (!hasOwn(norm, key)) {
          continue;
        }
        entry = table[key];
        total += norm[key] * entry.B * Math.pow(entry.Vm - vBar, 2) / (2.0 * entry.Vm);
      }
      return total;
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
        },
        senkov_kappa: {
          k1: null,
          k1_cr: null,
          g_ss_kj: null,
          g_im_kj: null,
          temperature: descriptors.King_temperature_K,
          verdict: null,
          value: null,
          threshold: null
        },
        tsai_sigma: {
          applies: descriptors.sigma_former_present === true,
          in_window: null,
          verdict: null,
          value: descriptors.VEC,
          threshold: TSAI_SIGMA_VEC_MIN + " ≤ VEC ≤ " + TSAI_SIGMA_VEC_MAX
        },
        sheikh_ductility: {
          verdict: null,
          value: descriptors.VEC,
          threshold: SHEIKH_DUCTILE_VEC
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

      // Senkov-Miracle 2016 kappa: direct Gibbs comparison at the shared
      // annealing temperature; k1/k1_cr reported when Hmix < 0 makes the
      // published ratio form meaningful.
      var kappa = result.senkov_kappa;
      if (
        isNumericValue(descriptors.Hmix) &&
        isNumericValue(descriptors.DeltaG_max) &&
        isNumericValue(descriptors.Smix) &&
        isNumericValue(descriptors.King_temperature_K)
      ) {
        var tsKj = descriptors.King_temperature_K * descriptors.Smix / 1000.0;
        kappa.g_ss_kj = descriptors.Hmix - tsKj;
        kappa.g_im_kj = descriptors.DeltaG_max - SENKOV_K2 * tsKj;
        kappa.verdict = kappa.g_ss_kj < kappa.g_im_kj ? "solid_solution" : "intermetallic";
        if (descriptors.Hmix < 0.0) {
          kappa.k1 = descriptors.DeltaG_max / descriptors.Hmix;
          kappa.k1_cr = 1.0 + (1.0 - SENKOV_K2) * tsKj / Math.abs(descriptors.Hmix);
          kappa.value = kappa.k1;
          kappa.threshold = kappa.k1_cr;
        }
      }

      // Tsai 2013 sigma window: only meaningful when Cr and/or V present.
      var sigma = result.tsai_sigma;
      if (isNumericValue(descriptors.VEC)) {
        sigma.in_window = descriptors.VEC >= TSAI_SIGMA_VEC_MIN && descriptors.VEC <= TSAI_SIGMA_VEC_MAX;
        if (!sigma.applies) {
          sigma.verdict = "not_applicable";
        } else {
          sigma.verdict = sigma.in_window ? "sigma_prone" : "sigma_unlikely";
        }
      }

      // Sheikh 2016 refractory ductility bands.
      if (isNumericValue(descriptors.VEC)) {
        if (descriptors.VEC < SHEIKH_DUCTILE_VEC) {
          result.sheikh_ductility.verdict = "ductile";
        } else if (descriptors.VEC >= SHEIKH_BRITTLE_VEC) {
          result.sheikh_ductility.verdict = "brittle";
        } else {
          result.sheikh_ductility.verdict = "borderline";
        }
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

      var chiMissing = elementsMissingChi(norm, elementData);
      var meanChi = null;
      var deltaChiValue = null;
      if (chiMissing.length) {
        warnings.push(
          "Missing Pauling electronegativity for " + chiMissing.join(", ") +
          "; the electronegativity descriptors are unavailable."
        );
      } else {
        meanChi = meanChiFromNormalized(norm, elementData);
        deltaChiValue = deltaChiFromNormalized(norm, elementData);
      }
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
      var lambdaSingh = lambdaFromNormalized(norm, elementData);
      var gammaWang = gammaFromNormalized(norm, elementData);
      var hElastic = hElasticFromNormalized(norm, options && options.mechanicsData);
      if (hElastic === null) {
        warnings.push(
          "Missing bulk modulus or molar volume for at least one element; the elastic-strain energy (Andreoli) is unavailable."
        );
      }
      var sigmaFormerPresent = false;
      (function () {
        var key;
        for (key in norm) {
          if (hasOwn(norm, key) && SIGMA_FORMER_ELEMENTS[key] === true) {
            sigmaFormerPresent = true;
            return;
          }
        }
      })();
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
        delta_chi: deltaChiValue,
        mean_chi: meanChi,
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
        King_temperature_K: kingTemperature,
        Lambda_singh: lambdaSingh,
        gamma_wang: gammaWang,
        H_elastic: hElastic,
        sigma_former_present: sigmaFormerPresent
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

    function deltaChi(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      ensureElementData(norm, elementData);
      var missing = elementsMissingChi(norm, elementData);
      if (missing.length) {
        throw new Error(
          "composition contains elements without electronegativity data: " + missing.join(", ")
        );
      }
      return deltaChiFromNormalized(norm, elementData);
    }

    function meanElectronegativity(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      ensureElementData(norm, elementData);
      var missing = elementsMissingChi(norm, elementData);
      if (missing.length) {
        throw new Error(
          "composition contains elements without electronegativity data: " + missing.join(", ")
        );
      }
      return meanChiFromNormalized(norm, elementData);
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

    function singhLambda(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      ensureElementData(norm, elementData);
      return lambdaFromNormalized(norm, elementData);
    }

    function wangGamma(composition, options) {
      var elementData = options && options.elementData ? options.elementData : DEFAULT_ELEMENT_DATA;
      var norm = normalizeComposition(composition);
      ensureElementData(norm, elementData);
      return gammaFromNormalized(norm, elementData);
    }

    function hElastic(composition, options) {
      var norm = normalizeComposition(composition);
      return hElasticFromNormalized(norm, options && options.mechanicsData);
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

    // ------------------------------------------------------------------
    // High-entropy-oxide (HEO) module — line-for-line port of the Python
    // hea_bench.oxides package. Parity-locked by
    // tests/test_web_oxides_parity.py; change both sides together.

    var OXIDE_R = 8.314462618;
    var OXYGEN_RADIUS = 1.4;
    var OXIDE_MAX_COMBINATIONS = 2000000;
    var OXIDE_CHARGE_TOLERANCE = 1e-6;

    // BEGIN GENERATED: OXIDE_ELEMENT_DATA
    // 94-element oxide table: Pauling electronegativity,
    // common/ICSD oxidation states, and Shannon (1976) effective ionic
    // radii (angstroms) nested as charge -> coordination number -> spin.
    // Generated from the Python library's vendored oxide_elements.json
    // (pymatgen 2025.10.7, MIT) by
    // tests/data/_sync_js_oxide_tables.py — do not edit by hand; the
    // oxide parity test asserts the two implementations agree.
    var OXIDE_ELEMENT_DATA = {
      Ac: { chi: 1.1, common: [3], icsd: [], radii: { "3": { "6": { "": 1.12 } } } },
      Ag: { chi: 1.93, common: [1], icsd: [1, 2, 3], radii: { "1": { "2": { "": 0.67 }, "4": { "": 1.0 }, "5": { "": 1.09 }, "6": { "": 1.15 }, "7": { "": 1.22 }, "8": { "": 1.28 } }, "2": { "6": { "": 0.94 } }, "3": { "6": { "": 0.75 } } } },
      Al: { chi: 1.61, common: [3], icsd: [3], radii: { "3": { "4": { "": 0.39 }, "5": { "": 0.48 }, "6": { "": 0.535 } } } },
      Am: { chi: 1.3, common: [3], icsd: [], radii: { "2": { "7": { "": 1.21 }, "8": { "": 1.26 }, "9": { "": 1.31 } }, "3": { "6": { "": 0.975 }, "8": { "": 1.09 } }, "4": { "6": { "": 0.85 }, "8": { "": 0.95 } } } },
      As: { chi: 2.18, common: [-3, 3, 5], icsd: [2, 3, 5, -2, -3, -1], radii: { "3": { "6": { "": 0.58 } }, "5": { "4": { "": 0.335 }, "6": { "": 0.46 } } } },
      At: { chi: 2.2, common: [-1, 1], icsd: [], radii: { "7": { "6": { "": 0.62 } } } },
      Au: { chi: 2.54, common: [3], icsd: [], radii: { "1": { "6": { "": 1.37 } }, "3": { "6": { "": 0.85 } }, "5": { "6": { "": 0.57 } } } },
      B: { chi: 2.04, common: [3], icsd: [3, -3], radii: { "3": { "3": { "": 0.01 }, "4": { "": 0.11 }, "6": { "": 0.27 } } } },
      Ba: { chi: 0.89, common: [2], icsd: [2], radii: { "2": { "6": { "": 1.35 }, "7": { "": 1.38 }, "8": { "": 1.42 }, "9": { "": 1.47 }, "10": { "": 1.52 }, "11": { "": 1.57 }, "12": { "": 1.61 } } } },
      Be: { chi: 1.57, common: [2], icsd: [2], radii: { "2": { "3": { "": 0.16 }, "4": { "": 0.27 }, "6": { "": 0.45 } } } },
      Bi: { chi: 2.02, common: [3], icsd: [1, 2, 3, 5], radii: { "3": { "5": { "": 0.96 }, "6": { "": 1.03 }, "8": { "": 1.17 } }, "5": { "6": { "": 0.76 } } } },
      Bk: { chi: 1.3, common: [3], icsd: [], radii: { "3": { "6": { "": 0.96 } }, "4": { "6": { "": 0.83 }, "8": { "": 0.93 } } } },
      Br: { chi: 2.96, common: [-1, 1, 3, 5, 7], icsd: [5, -1], radii: { "-1": { "6": { "": 1.96 } }, "7": { "4": { "": 0.25 }, "6": { "": 0.39 } } } },
      C: { chi: 2.55, common: [-4, 4], icsd: [2, 3, 4, -4, -3, -2], radii: { "4": { "3": { "": -0.08 }, "4": { "": 0.15 }, "6": { "": 0.16 } } } },
      Ca: { chi: 1, common: [2], icsd: [2], radii: { "2": { "6": { "": 1.0 }, "7": { "": 1.06 }, "8": { "": 1.12 }, "9": { "": 1.18 }, "10": { "": 1.23 }, "12": { "": 1.34 } } } },
      Cd: { chi: 1.69, common: [2], icsd: [2], radii: { "2": { "4": { "": 0.78 }, "5": { "": 0.87 }, "6": { "": 0.95 }, "7": { "": 1.03 }, "8": { "": 1.1 }, "12": { "": 1.31 } } } },
      Ce: { chi: 1.12, common: [3, 4], icsd: [3, 4], radii: { "3": { "6": { "": 1.01 }, "7": { "": 1.07 }, "8": { "": 1.143 }, "9": { "": 1.196 }, "10": { "": 1.25 }, "12": { "": 1.34 } }, "4": { "6": { "": 0.87 }, "8": { "": 0.97 }, "10": { "": 1.07 }, "12": { "": 1.14 } } } },
      Cf: { chi: 1.3, common: [3], icsd: [], radii: { "3": { "6": { "": 0.95 } }, "4": { "6": { "": 0.821 }, "8": { "": 0.92 } } } },
      Cl: { chi: 3.16, common: [-1, 1, 3, 5, 7], icsd: [-1], radii: { "-1": { "6": { "": 1.81 } }, "7": { "4": { "": 0.08 }, "6": { "": 0.27 } } } },
      Cm: { chi: 1.3, common: [3], icsd: [], radii: { "3": { "6": { "": 0.97 } }, "4": { "6": { "": 0.85 }, "8": { "": 0.95 } } } },
      Co: { chi: 1.88, common: [2, 3], icsd: [1, 2, 3, 4], radii: { "2": { "4": { "High Spin": 0.58 }, "5": { "": 0.67 }, "6": { "High Spin": 0.745, "Low Spin": 0.65 }, "8": { "": 0.9 } }, "3": { "6": { "High Spin": 0.61, "Low Spin": 0.545 } }, "4": { "4": { "": 0.4 }, "6": { "High Spin": 0.53 } } } },
      Cr: { chi: 1.66, common: [3, 6], icsd: [2, 3, 4, 5, 6], radii: { "2": { "6": { "High Spin": 0.8, "Low Spin": 0.73 } }, "3": { "6": { "": 0.615 } }, "4": { "4": { "": 0.41 }, "6": { "": 0.55 } }, "5": { "4": { "": 0.345 }, "6": { "": 0.49 }, "8": { "": 0.57 } }, "6": { "4": { "": 0.26 }, "6": { "": 0.44 } } } },
      Cs: { chi: 0.79, common: [1], icsd: [1], radii: { "1": { "6": { "": 1.67 }, "8": { "": 1.74 }, "9": { "": 1.78 }, "10": { "": 1.81 }, "11": { "": 1.85 }, "12": { "": 1.88 } } } },
      Cu: { chi: 1.9, common: [2], icsd: [1, 2, 3], radii: { "1": { "2": { "": 0.46 }, "4": { "": 0.6 }, "6": { "": 0.77 } }, "2": { "4": { "": 0.57 }, "5": { "": 0.65 }, "6": { "": 0.73 } }, "3": { "6": { "Low Spin": 0.54 } } } },
      Dy: { chi: 1.22, common: [3], icsd: [3], radii: { "2": { "6": { "": 1.07 }, "7": { "": 1.13 }, "8": { "": 1.19 } }, "3": { "6": { "": 0.912 }, "7": { "": 0.97 }, "8": { "": 1.027 }, "9": { "": 1.083 } } } },
      Er: { chi: 1.24, common: [3], icsd: [3], radii: { "3": { "6": { "": 0.89 }, "7": { "": 0.945 }, "8": { "": 1.004 }, "9": { "": 1.062 } } } },
      Eu: { chi: 1.2, common: [2, 3], icsd: [2, 3], radii: { "2": { "6": { "": 1.17 }, "7": { "": 1.2 }, "8": { "": 1.25 }, "9": { "": 1.3 }, "10": { "": 1.35 } }, "3": { "6": { "": 0.947 }, "8": { "": 1.066 }, "9": { "": 1.12 } } } },
      F: { chi: 3.98, common: [-1], icsd: [-1], radii: { "-1": { "2": { "": 1.285 }, "3": { "": 1.3 }, "4": { "": 1.31 }, "6": { "": 1.33 } }, "7": { "6": { "": 0.08 } } } },
      Fe: { chi: 1.83, common: [2, 3], icsd: [2, 3], radii: { "2": { "4": { "High Spin": 0.63 }, "6": { "High Spin": 0.78, "Low Spin": 0.61 }, "8": { "High Spin": 0.92 } }, "3": { "4": { "High Spin": 0.49 }, "5": { "": 0.58 }, "6": { "High Spin": 0.645, "Low Spin": 0.55 }, "8": { "High Spin": 0.78 } }, "4": { "6": { "": 0.585 } }, "6": { "4": { "": 0.25 } } } },
      Fr: { chi: 0.7, common: [1], icsd: [], radii: { "1": { "6": { "": 1.8 } } } },
      Ga: { chi: 1.81, common: [3], icsd: [2, 3], radii: { "3": { "4": { "": 0.47 }, "5": { "": 0.55 }, "6": { "": 0.62 } } } },
      Gd: { chi: 1.2, common: [3], icsd: [3], radii: { "3": { "6": { "": 0.938 }, "7": { "": 1.0 }, "8": { "": 1.053 }, "9": { "": 1.107 } } } },
      Ge: { chi: 2.01, common: [-4, 2, 4], icsd: [2, 3, 4], radii: { "2": { "6": { "": 0.73 } }, "4": { "4": { "": 0.39 }, "6": { "": 0.53 } } } },
      H: { chi: 2.2, common: [-1, 1], icsd: [1, -1], radii: { "1": { "1": { "": -0.38 }, "2": { "": -0.18 } } } },
      Hf: { chi: 1.3, common: [4], icsd: [4], radii: { "4": { "4": { "": 0.58 }, "6": { "": 0.71 }, "7": { "": 0.76 }, "8": { "": 0.83 } } } },
      Hg: { chi: 2, common: [1, 2], icsd: [1, 2], radii: { "1": { "3": { "": 0.97 }, "6": { "": 1.19 } }, "2": { "2": { "": 0.69 }, "4": { "": 0.96 }, "6": { "": 1.02 }, "8": { "": 1.14 } } } },
      Ho: { chi: 1.23, common: [3], icsd: [3], radii: { "3": { "6": { "": 0.901 }, "8": { "": 1.015 }, "9": { "": 1.072 }, "10": { "": 1.12 } } } },
      I: { chi: 2.66, common: [-1, 1, 3, 5, 7], icsd: [5, -1], radii: { "-1": { "6": { "": 2.2 } }, "5": { "6": { "": 0.95 } }, "7": { "4": { "": 0.42 }, "6": { "": 0.53 } } } },
      In: { chi: 1.78, common: [3], icsd: [1, 2, 3], radii: { "3": { "4": { "": 0.62 }, "6": { "": 0.8 }, "8": { "": 0.92 } } } },
      Ir: { chi: 2.2, common: [3, 4], icsd: [3, 4, 5], radii: { "3": { "6": { "": 0.68 } }, "4": { "6": { "": 0.625 } }, "5": { "6": { "": 0.57 } } } },
      K: { chi: 0.82, common: [1], icsd: [1], radii: { "1": { "4": { "": 1.37 }, "6": { "": 1.38 }, "7": { "": 1.46 }, "8": { "": 1.51 }, "9": { "": 1.55 }, "10": { "": 1.59 }, "12": { "": 1.64 } } } },
      La: { chi: 1.1, common: [3], icsd: [2, 3], radii: { "3": { "6": { "": 1.032 }, "7": { "": 1.1 }, "8": { "": 1.16 }, "9": { "": 1.216 }, "10": { "": 1.27 }, "12": { "": 1.36 } } } },
      Li: { chi: 0.98, common: [1], icsd: [1], radii: { "1": { "4": { "": 0.59 }, "6": { "": 0.76 }, "8": { "": 0.92 } } } },
      Lu: { chi: 1.27, common: [3], icsd: [3], radii: { "3": { "6": { "": 0.861 }, "8": { "": 0.977 }, "9": { "": 1.032 } } } },
      Mg: { chi: 1.31, common: [2], icsd: [2], radii: { "2": { "4": { "": 0.57 }, "5": { "": 0.66 }, "6": { "": 0.72 }, "8": { "": 0.89 } } } },
      Mn: { chi: 1.55, common: [2, 4, 7], icsd: [2, 3, 4, 7], radii: { "2": { "4": { "High Spin": 0.66 }, "5": { "High Spin": 0.75 }, "6": { "High Spin": 0.83, "Low Spin": 0.67 }, "7": { "High Spin": 0.9 }, "8": { "": 0.96 } }, "3": { "5": { "": 0.58 }, "6": { "High Spin": 0.645, "Low Spin": 0.58 } }, "4": { "4": { "": 0.39 }, "6": { "": 0.53 } }, "5": { "4": { "": 0.33 } }, "6": { "4": { "": 0.255 } }, "7": { "4": { "": 0.25 }, "6": { "": 0.46 } } } },
      Mo: { chi: 2.16, common: [4, 6], icsd: [2, 3, 4, 5, 6], radii: { "3": { "6": { "": 0.69 } }, "4": { "6": { "": 0.65 } }, "5": { "4": { "": 0.46 }, "6": { "": 0.61 } }, "6": { "4": { "": 0.41 }, "5": { "": 0.5 }, "6": { "": 0.59 }, "7": { "": 0.73 } } } },
      N: { chi: 3.04, common: [-3, 3, 5], icsd: [1, 3, 5, -1, -3, -2], radii: { "-3": { "4": { "": 1.46 } }, "3": { "6": { "": 0.16 } }, "5": { "3": { "": -0.104 }, "6": { "": 0.13 } } } },
      Na: { chi: 0.93, common: [1], icsd: [1], radii: { "1": { "4": { "": 0.99 }, "5": { "": 1.0 }, "6": { "": 1.02 }, "7": { "": 1.12 }, "8": { "": 1.18 }, "9": { "": 1.24 }, "12": { "": 1.39 } } } },
      Nb: { chi: 1.6, common: [5], icsd: [2, 3, 4, 5], radii: { "3": { "6": { "": 0.72 } }, "4": { "6": { "": 0.68 }, "8": { "": 0.79 } }, "5": { "4": { "": 0.48 }, "6": { "": 0.64 }, "7": { "": 0.69 }, "8": { "": 0.74 } } } },
      Nd: { chi: 1.14, common: [3], icsd: [2, 3], radii: { "2": { "8": { "": 1.29 }, "9": { "": 1.35 } }, "3": { "6": { "": 0.983 }, "8": { "": 1.109 }, "9": { "": 1.163 }, "12": { "": 1.27 } } } },
      Ni: { chi: 1.91, common: [2], icsd: [1, 2, 3, 4], radii: { "2": { "4": { "": 0.55 }, "5": { "": 0.63 }, "6": { "": 0.69 } }, "3": { "6": { "High Spin": 0.6, "Low Spin": 0.56 } }, "4": { "6": { "Low Spin": 0.48 } } } },
      No: { chi: 1.3, common: [3], icsd: [], radii: { "2": { "6": { "": 1.1 } } } },
      Np: { chi: 1.36, common: [5], icsd: [], radii: { "2": { "6": { "": 1.1 } }, "3": { "6": { "": 1.01 } }, "4": { "6": { "": 0.87 }, "8": { "": 0.98 } }, "5": { "6": { "": 0.75 } }, "6": { "6": { "": 0.72 } }, "7": { "6": { "": 0.71 } } } },
      O: { chi: 3.44, common: [-2], icsd: [-2], radii: { "-2": { "2": { "": 1.35 }, "3": { "": 1.36 }, "4": { "": 1.38 }, "6": { "": 1.4 }, "8": { "": 1.42 } } } },
      Os: { chi: 2.2, common: [4], icsd: [], radii: { "4": { "6": { "": 0.63 } }, "5": { "6": { "": 0.575 } }, "6": { "5": { "": 0.49 }, "6": { "": 0.545 } }, "7": { "6": { "": 0.525 } }, "8": { "4": { "": 0.39 } } } },
      P: { chi: 2.19, common: [-3, 3, 5], icsd: [3, 4, 5, -2, -3, -1], radii: { "3": { "6": { "": 0.44 } }, "5": { "4": { "": 0.17 }, "5": { "": 0.29 }, "6": { "": 0.38 } } } },
      Pa: { chi: 1.5, common: [5], icsd: [], radii: { "3": { "6": { "": 1.04 } }, "4": { "6": { "": 0.9 }, "8": { "": 1.01 } }, "5": { "6": { "": 0.78 }, "8": { "": 0.91 }, "9": { "": 0.95 } } } },
      Pb: { chi: 2.33, common: [2, 4], icsd: [2, 4], radii: { "2": { "6": { "": 1.19 }, "7": { "": 1.23 }, "8": { "": 1.29 }, "9": { "": 1.35 }, "10": { "": 1.4 }, "11": { "": 1.45 }, "12": { "": 1.49 } }, "4": { "4": { "": 0.65 }, "5": { "": 0.73 }, "6": { "": 0.775 }, "8": { "": 0.94 } } } },
      Pd: { chi: 2.2, common: [2, 4], icsd: [2, 4], radii: { "1": { "2": { "": 0.59 } }, "2": { "6": { "": 0.86 } }, "3": { "6": { "": 0.76 } }, "4": { "6": { "": 0.615 } } } },
      Pm: { chi: 1.13, common: [3], icsd: [], radii: { "3": { "6": { "": 0.97 }, "8": { "": 1.093 }, "9": { "": 1.144 } } } },
      Po: { chi: 2, common: [-2, 2, 4], icsd: [], radii: { "4": { "6": { "": 0.94 }, "8": { "": 1.08 } }, "6": { "6": { "": 0.67 } } } },
      Pr: { chi: 1.13, common: [3], icsd: [3, 4], radii: { "3": { "6": { "": 0.99 }, "8": { "": 1.126 }, "9": { "": 1.179 } }, "4": { "6": { "": 0.85 }, "8": { "": 0.96 } } } },
      Pt: { chi: 2.28, common: [2, 4], icsd: [], radii: { "2": { "6": { "": 0.8 } }, "4": { "6": { "": 0.625 } }, "5": { "6": { "": 0.57 } } } },
      Pu: { chi: 1.28, common: [4], icsd: [], radii: { "3": { "6": { "": 1.0 } }, "4": { "6": { "": 0.86 }, "8": { "": 0.96 } }, "5": { "6": { "": 0.74 } }, "6": { "6": { "": 0.71 } } } },
      Ra: { chi: 0.9, common: [2], icsd: [], radii: { "2": { "8": { "": 1.48 }, "12": { "": 1.7 } } } },
      Rb: { chi: 0.82, common: [1], icsd: [1], radii: { "1": { "6": { "": 1.52 }, "7": { "": 1.56 }, "8": { "": 1.61 }, "9": { "": 1.63 }, "10": { "": 1.66 }, "11": { "": 1.69 }, "12": { "": 1.72 }, "14": { "": 1.83 } } } },
      Re: { chi: 1.9, common: [4], icsd: [3, 4, 5, 6, 7], radii: { "4": { "6": { "": 0.63 } }, "5": { "6": { "": 0.58 } }, "6": { "6": { "": 0.55 } }, "7": { "4": { "": 0.38 }, "6": { "": 0.53 } } } },
      Rh: { chi: 2.28, common: [3], icsd: [3, 4], radii: { "3": { "6": { "": 0.665 } }, "4": { "6": { "": 0.6 } }, "5": { "6": { "": 0.55 } } } },
      Ru: { chi: 2.2, common: [3, 4], icsd: [2, 3, 4, 5, 6], radii: { "3": { "6": { "": 0.68 } }, "4": { "6": { "": 0.62 } }, "5": { "6": { "": 0.565 } }, "7": { "4": { "": 0.38 } }, "8": { "4": { "": 0.36 } } } },
      S: { chi: 2.58, common: [-2, 2, 4, 6], icsd: [-1, 2, 4, -2, 6], radii: { "-2": { "6": { "": 1.84 } }, "4": { "6": { "": 0.37 } }, "6": { "4": { "": 0.12 }, "6": { "": 0.29 } } } },
      Sb: { chi: 2.05, common: [-3, 3, 5], icsd: [-2, 3, 5, -1, -3], radii: { "3": { "5": { "": 0.8 }, "6": { "": 0.76 } }, "5": { "6": { "": 0.6 } } } },
      Sc: { chi: 1.36, common: [3], icsd: [2, 3], radii: { "3": { "6": { "": 0.745 }, "8": { "": 0.87 } } } },
      Se: { chi: 2.55, common: [-2, 2, 4, 6], icsd: [-1, 4, -2, 6], radii: { "-2": { "6": { "": 1.98 } }, "4": { "6": { "": 0.5 } }, "6": { "4": { "": 0.28 }, "6": { "": 0.42 } } } },
      Si: { chi: 1.9, common: [-4, 4], icsd: [-4, 4], radii: { "4": { "4": { "": 0.26 }, "6": { "": 0.4 } } } },
      Sm: { chi: 1.17, common: [3], icsd: [2, 3], radii: { "2": { "7": { "": 1.22 }, "8": { "": 1.27 }, "9": { "": 1.32 } }, "3": { "6": { "": 0.958 }, "7": { "": 1.02 }, "8": { "": 1.079 }, "9": { "": 1.132 }, "12": { "": 1.24 } } } },
      Sn: { chi: 1.96, common: [-4, 2, 4], icsd: [2, 3, 4], radii: { "4": { "4": { "": 0.55 }, "5": { "": 0.62 }, "6": { "": 0.69 }, "7": { "": 0.75 }, "8": { "": 0.81 } } } },
      Sr: { chi: 0.95, common: [2], icsd: [2], radii: { "2": { "6": { "": 1.18 }, "7": { "": 1.21 }, "8": { "": 1.26 }, "9": { "": 1.31 }, "10": { "": 1.36 }, "12": { "": 1.44 } } } },
      Ta: { chi: 1.5, common: [5], icsd: [3, 4, 5], radii: { "3": { "6": { "": 0.72 } }, "4": { "6": { "": 0.68 } }, "5": { "6": { "": 0.64 }, "7": { "": 0.69 }, "8": { "": 0.74 } } } },
      Tb: { chi: 1.1, common: [3], icsd: [3, 4], radii: { "3": { "6": { "": 0.923 }, "7": { "": 0.98 }, "8": { "": 1.04 }, "9": { "": 1.095 } }, "4": { "6": { "": 0.76 }, "8": { "": 0.88 } } } },
      Tc: { chi: 1.9, common: [4, 7], icsd: [], radii: { "4": { "6": { "": 0.645 } }, "5": { "6": { "": 0.6 } }, "7": { "4": { "": 0.37 }, "6": { "": 0.56 } } } },
      Te: { chi: 2.1, common: [-2, 2, 4, 6], icsd: [-2, 4, -1, 6], radii: { "-2": { "6": { "": 2.21 } }, "4": { "3": { "": 0.52 }, "4": { "": 0.66 }, "6": { "": 0.97 } }, "6": { "4": { "": 0.43 }, "6": { "": 0.56 } } } },
      Th: { chi: 1.3, common: [4], icsd: [4], radii: { "4": { "6": { "": 0.94 }, "8": { "": 1.05 }, "9": { "": 1.09 }, "10": { "": 1.13 }, "11": { "": 1.18 }, "12": { "": 1.21 } } } },
      Ti: { chi: 1.54, common: [4], icsd: [2, 3, 4], radii: { "2": { "6": { "": 0.86 } }, "3": { "6": { "": 0.67 } }, "4": { "4": { "": 0.42 }, "5": { "": 0.51 }, "6": { "": 0.605 }, "8": { "": 0.74 } } } },
      Tl: { chi: 1.62, common: [1, 3], icsd: [1, 3], radii: { "1": { "6": { "": 1.5 }, "8": { "": 1.59 }, "12": { "": 1.7 } }, "3": { "4": { "": 0.75 }, "6": { "": 0.885 }, "8": { "": 0.98 } } } },
      Tm: { chi: 1.25, common: [3], icsd: [3], radii: { "2": { "6": { "": 1.03 }, "7": { "": 1.09 } }, "3": { "6": { "": 0.88 }, "8": { "": 0.994 }, "9": { "": 1.052 } } } },
      U: { chi: 1.38, common: [6], icsd: [3, 4, 5, 6], radii: { "3": { "6": { "": 1.025 } }, "4": { "6": { "": 0.89 }, "7": { "": 0.95 }, "8": { "": 1.0 }, "9": { "": 1.05 }, "12": { "": 1.17 } }, "5": { "6": { "": 0.76 }, "7": { "": 0.84 } }, "6": { "2": { "": 0.45 }, "4": { "": 0.52 }, "6": { "": 0.73 }, "7": { "": 0.81 }, "8": { "": 0.86 } } } },
      V: { chi: 1.63, common: [5], icsd: [2, 3, 4, 5], radii: { "2": { "6": { "": 0.79 } }, "3": { "6": { "": 0.64 } }, "4": { "5": { "": 0.53 }, "6": { "": 0.58 }, "8": { "": 0.72 } }, "5": { "4": { "": 0.355 }, "5": { "": 0.46 }, "6": { "": 0.54 } } } },
      W: { chi: 2.36, common: [4, 6], icsd: [2, 3, 4, 5, 6], radii: { "4": { "6": { "": 0.66 } }, "5": { "6": { "": 0.62 } }, "6": { "4": { "": 0.42 }, "5": { "": 0.51 }, "6": { "": 0.6 } } } },
      Xe: { chi: 2.6, common: [], icsd: [], radii: { "8": { "4": { "": 0.4 }, "6": { "": 0.48 } } } },
      Y: { chi: 1.22, common: [3], icsd: [3], radii: { "3": { "6": { "": 0.9 }, "7": { "": 0.96 }, "8": { "": 1.019 }, "9": { "": 1.075 } } } },
      Yb: { chi: 1.1, common: [3], icsd: [2, 3], radii: { "2": { "6": { "": 1.02 }, "7": { "": 1.08 }, "8": { "": 1.14 } }, "3": { "6": { "": 0.868 }, "7": { "": 0.925 }, "8": { "": 0.985 }, "9": { "": 1.042 } } } },
      Zn: { chi: 1.65, common: [2], icsd: [2], radii: { "2": { "4": { "": 0.6 }, "5": { "": 0.68 }, "6": { "": 0.74 }, "8": { "": 0.9 } } } },
      Zr: { chi: 1.33, common: [4], icsd: [2, 3, 4], radii: { "4": { "4": { "": 0.59 }, "5": { "": 0.66 }, "6": { "": 0.72 }, "7": { "": 0.78 }, "8": { "": 0.84 }, "9": { "": 0.89 } } } }
    };
    // END GENERATED: OXIDE_ELEMENT_DATA

    function oxideChargeLabel(charge) {
      return (charge >= 0 ? "+" : "") + String(charge);
    }

    function oxidePlusG(value) {
      var v = Number(value.toPrecision(6));
      return (v >= 0 ? "+" : "") + String(v);
    }

    function oxideShannonRadius(element, charge, coordination, spin) {
      var spinPref = spin || "high";
      if (spinPref !== "high" && spinPref !== "low") {
        throw new Error('spin must be "high" or "low", got ' + JSON.stringify(spin));
      }
      var entry = OXIDE_ELEMENT_DATA[element];
      if (!entry) {
        throw new Error("element '" + element + "' is not in the vendored oxide element table");
      }
      var byCharge = entry.radii[String(parseInt(charge, 10))];
      if (!byCharge) {
        var have = Object.keys(entry.radii).map(Number).sort(function (a, b) { return a - b; });
        throw new Error(
          "no Shannon radius for " + element + " in oxidation state " +
          oxideChargeLabel(charge) + " (tabulated states: " + have.join(", ") + ")"
        );
      }
      var warnings = [];
      var available = Object.keys(byCharge).map(Number);
      var usedCn;
      if (available.indexOf(coordination) >= 0) {
        usedCn = coordination;
      } else {
        var best = null;
        available.forEach(function (n) {
          if (best === null) { best = n; return; }
          var dn = Math.abs(n - coordination);
          var db = Math.abs(best - coordination);
          if (dn < db || (dn === db && n > best)) { best = n; }
        });
        usedCn = best;
        warnings.push(
          element + oxideChargeLabel(charge) + ": no Shannon radius at CN=" + coordination +
          "; using the nearest tabulated CN=" + usedCn
        );
      }
      var spins = byCharge[String(usedCn)];
      var wanted = spinPref === "high" ? "High Spin" : "Low Spin";
      var radius;
      if (Object.prototype.hasOwnProperty.call(spins, wanted)) {
        radius = spins[wanted];
      } else if (Object.prototype.hasOwnProperty.call(spins, "")) {
        radius = spins[""];
      } else {
        var fallbackKey = Object.keys(spins).sort()[0];
        radius = spins[fallbackKey];
        warnings.push(
          element + oxideChargeLabel(charge) + " CN=" + usedCn + ": no " + wanted.toLowerCase() +
          " entry; using the " + (fallbackKey.toLowerCase() || "unspecified-spin") + " radius"
        );
      }
      return { radius: radius, warnings: warnings };
    }

    function oxideCandidates(element) {
      var entry = OXIDE_ELEMENT_DATA[element];
      if (!entry) {
        throw new Error("element '" + element + "' is not in the vendored oxide element table");
      }
      var withRadius = {};
      Object.keys(entry.radii).forEach(function (q) {
        var n = parseInt(q, 10);
        if (n > 0) { withRadius[n] = true; }
      });
      var common = entry.common.filter(function (q) { return withRadius[q] === true; });
      var widened = common.slice();
      entry.icsd.forEach(function (q) {
        if (q > 0 && withRadius[q] === true && widened.indexOf(q) < 0) { widened.push(q); }
      });
      Object.keys(withRadius).map(Number).sort(function (a, b) { return a - b; }).forEach(function (q) {
        if (widened.indexOf(q) < 0) { widened.push(q); }
      });
      if (!widened.length) {
        throw new Error(element + " has no positive oxidation state with a Shannon radius");
      }
      return { common: common, widened: widened };
    }

    function oxideAssignStates(moles, targetCharge, allowed, groups) {
      var elements = Object.keys(moles).sort();
      if (!elements.length) { throw new Error("moles must be non-empty"); }
      var pins = allowed || {};

      var commonLists = [];
      var widenedLists = [];
      elements.forEach(function (el) {
        if (pins[el] !== undefined && pins[el] !== null) {
          var pinned = pins[el].map(function (q) { return parseInt(q, 10); });
          if (!pinned.length) { throw new Error("allowed['" + el + "'] must be non-empty"); }
          commonLists.push(pinned);
          widenedLists.push(pinned);
        } else {
          var cands = oxideCandidates(el);
          commonLists.push(cands.common.length ? cands.common : cands.widened);
          widenedLists.push(cands.widened);
        }
      });

      function totalFor(combo) {
        var total = 0;
        for (var i = 0; i < elements.length; i++) { total += moles[elements[i]] * combo[i]; }
        return total;
      }

      function eachCombo(lists, fn) {
        var idx = lists.map(function () { return 0; });
        for (;;) {
          fn(idx.map(function (v, i) { return lists[i][v]; }));
          var k = lists.length - 1;
          for (;;) {
            if (k < 0) { return; }
            idx[k] += 1;
            if (idx[k] < lists[k].length) { break; }
            idx[k] = 0;
            k -= 1;
          }
        }
      }

      function solve(lists) {
        var nCombos = 1;
        lists.forEach(function (list) { nCombos *= list.length; });
        if (nCombos > OXIDE_MAX_COMBINATIONS) {
          throw new Error(
            "oxidation-state search space too large (" + nCombos +
            " combinations); pin states for some elements via `allowed`"
          );
        }
        var found = [];
        eachCombo(lists, function (combo) {
          if (Math.abs(totalFor(combo) - targetCharge) < OXIDE_CHARGE_TOLERANCE) {
            found.push(combo.slice());
          }
        });
        return found;
      }

      var warnings = [];
      var solutions = solve(commonLists);
      if (!solutions.length) {
        solutions = solve(widenedLists);
        if (solutions.length) {
          warnings.push(
            "no charge-neutral assignment using only common oxidation states; " +
            "a less common state was used"
          );
        }
      }
      if (!solutions.length) {
        var bestTotal = null;
        eachCombo(widenedLists, function (combo) {
          var total = totalFor(combo);
          if (bestTotal === null ||
              Math.abs(total - targetCharge) < Math.abs(bestTotal - targetCharge)) {
            bestTotal = total;
          }
        });
        throw new Error(
          "no oxidation-state assignment reaches total charge " + oxidePlusG(targetCharge) +
          " (closest achievable: " + oxidePlusG(bestTotal) + "); check the composition, " +
          "the oxygen content, or pass explicit states via `allowed`"
        );
      }

      var rank = {};
      elements.forEach(function (el, j) {
        rank[el] = {};
        widenedLists[j].forEach(function (q, i) { rank[el][q] = i; });
      });
      var groupOf = {};
      elements.forEach(function (el) {
        groupOf[el] = groups && groups[el] !== undefined ? groups[el] : "";
      });
      var labels = [];
      elements.forEach(function (el) {
        if (labels.indexOf(groupOf[el]) < 0) { labels.push(groupOf[el]); }
      });
      labels.sort();

      function score(combo) {
        var states = {};
        elements.forEach(function (el, i) { states[el] = combo[i]; });
        var variance = 0;
        labels.forEach(function (label) {
          var members = elements.filter(function (el) { return groupOf[el] === label; });
          var weight = 0;
          members.forEach(function (el) { weight += moles[el]; });
          var meanQ = 0;
          members.forEach(function (el) { meanQ += moles[el] * states[el]; });
          meanQ /= weight;
          members.forEach(function (el) {
            variance += moles[el] * (states[el] - meanQ) * (states[el] - meanQ);
          });
        });
        var commonness = 0;
        var chiWeighted = 0;
        elements.forEach(function (el, i) {
          commonness += moles[el] * rank[el][combo[i]];
          chiWeighted += moles[el] * combo[i] * (OXIDE_ELEMENT_DATA[el].chi || 0);
        });
        return [variance, commonness, chiWeighted, combo];
      }

      function scoreLess(a, b) {
        for (var i = 0; i < 3; i++) {
          if (a[i] !== b[i]) { return a[i] < b[i]; }
        }
        for (var j = 0; j < a[3].length; j++) {
          if (a[3][j] !== b[3][j]) { return a[3][j] < b[3][j]; }
        }
        return false;
      }

      var bestCombo = solutions[0];
      var bestScore = score(bestCombo);
      for (var s = 1; s < solutions.length; s++) {
        var candidateScore = score(solutions[s]);
        if (scoreLess(candidateScore, bestScore)) {
          bestScore = candidateScore;
          bestCombo = solutions[s];
        }
      }
      if (solutions.length > 1) {
        warnings.push(
          solutions.length + " charge-neutral assignments exist; chose the most " +
          "charge-uniform, most common one (pass `allowed` to override)"
        );
      }
      var statesOut = {};
      elements.forEach(function (el, i) { statesOut[el] = bestCombo[i]; });
      return { states: statesOut, warnings: warnings };
    }

    function oxideNormalizeSite(fractions) {
      var keys = Object.keys(fractions || {});
      if (!keys.length) { throw new Error("sublattice composition must be non-empty"); }
      var total = 0;
      keys.forEach(function (el) {
        var v = Number(fractions[el]);
        if (v < 0) { throw new Error("occupancies must be non-negative"); }
        total += v;
      });
      if (!(total > 0)) { throw new Error("occupancies must sum to a positive number"); }
      var norm = {};
      keys.forEach(function (el) {
        var v = Number(fractions[el]);
        if (v > 0) { norm[el] = v / total; }
      });
      return norm;
    }

    function oxideSublatticeEntropy(sublattices, multiplicities, per) {
      var mode = per || "formula";
      if (mode !== "formula" && mode !== "cation") {
        throw new Error('per must be "formula" or "cation", got ' + JSON.stringify(per));
      }
      var total = 0;
      var sites = 0;
      Object.keys(sublattices).forEach(function (label) {
        var a = multiplicities[label];
        var norm = oxideNormalizeSite(sublattices[label]);
        var sum = 0;
        Object.keys(norm).forEach(function (el) {
          var x = norm[el];
          sum += -x * Math.log(x);
        });
        total += a * sum;
        sites += a;
      });
      var entropy = OXIDE_R * total;
      return mode === "formula" ? entropy : entropy / sites;
    }

    function oxideSizeDisorder(fractions, radii) {
      var norm = oxideNormalizeSite(fractions);
      var rMean = 0;
      Object.keys(norm).forEach(function (el) { rMean += norm[el] * radii[el]; });
      var inner = 0;
      Object.keys(norm).forEach(function (el) {
        var dev = 1 - radii[el] / rMean;
        inner += norm[el] * dev * dev;
      });
      return 100 * Math.sqrt(Math.max(inner, 0));
    }

    function oxideCombinedSizeDisorder(deltas) {
      var sum = 0;
      deltas.forEach(function (d) { sum += d * d; });
      return Math.sqrt(sum);
    }

    function oxideRadiusSampleStd(radii) {
      if (radii.length < 2) {
        throw new Error("need at least two cations for a standard deviation");
      }
      var mean = 0;
      radii.forEach(function (r) { mean += r; });
      mean /= radii.length;
      var sum = 0;
      radii.forEach(function (r) { sum += (r - mean) * (r - mean); });
      return Math.sqrt(sum / (radii.length - 1));
    }

    function goldschmidtT(rA, rB, rO) {
      var anion = rO === undefined ? OXYGEN_RADIUS : rO;
      return (rA + anion) / (Math.sqrt(2) * (rB + anion));
    }

    function octahedralFactor(rB, rO) {
      var anion = rO === undefined ? OXYGEN_RADIUS : rO;
      return rB / anion;
    }

    function bartelTau(rA, rB, nA, rX) {
      var anion = rX === undefined ? OXYGEN_RADIUS : rX;
      if (rA <= rB) {
        throw new Error(
          "bartel_tau requires rA > rB (got rA=" + rA.toFixed(3) + ", rB=" + rB.toFixed(3) +
          "); the larger cation belongs on the A site"
        );
      }
      var ratio = rA / rB;
      return anion / rB - nA * (nA - ratio / Math.log(ratio));
    }

    function oxideRadiusRatio(rA, rB) {
      return rA / rB;
    }

    function oxideMeanChi(fractions) {
      var norm = oxideNormalizeSite(fractions);
      var missing = [];
      Object.keys(norm).forEach(function (el) {
        if (OXIDE_ELEMENT_DATA[el].chi === null || OXIDE_ELEMENT_DATA[el].chi === undefined) {
          missing.push(el);
        }
      });
      if (missing.length) {
        missing.sort();
        throw new Error("no Pauling electronegativity for: " + missing.join(", "));
      }
      var mean = 0;
      Object.keys(norm).forEach(function (el) { mean += norm[el] * OXIDE_ELEMENT_DATA[el].chi; });
      return mean;
    }

    function oxideDeltaChi(fractions) {
      var norm = oxideNormalizeSite(fractions);
      var chiBar = oxideMeanChi(norm);
      var inner = 0;
      Object.keys(norm).forEach(function (el) {
        var dev = OXIDE_ELEMENT_DATA[el].chi - chiBar;
        inner += norm[el] * dev * dev;
      });
      return Math.sqrt(Math.max(inner, 0));
    }

    function oxideRadiiFor(norm, states, coordination, spin, warnings) {
      var radii = {};
      Object.keys(norm).forEach(function (el) {
        var result = oxideShannonRadius(el, states[el], coordination, spin);
        radii[el] = result.radius;
        result.warnings.forEach(function (w) { warnings.push(w); });
      });
      return radii;
    }

    function oxideEntropyVerdict(sPerSite) {
      if (sPerSite >= 1.5 * OXIDE_R) { return "high-entropy"; }
      if (sPerSite >= 1.36 * OXIDE_R) { return "medium-entropy"; }
      return "low-entropy";
    }

    function oxideWindowVerdict(value, low, high) {
      if (value < low) { return "below-window"; }
      if (value > high) { return "above-window"; }
      return "within-window";
    }

    function oxideChiStats(pooled, warnings) {
      try {
        return { mean: oxideMeanChi(pooled), delta: oxideDeltaChi(pooled) };
      } catch (error) {
        warnings.push(error.message);
        return { mean: null, delta: null };
      }
    }

    function oxideMeanRadius(norm, radii) {
      var mean = 0;
      Object.keys(norm).forEach(function (el) { mean += norm[el] * radii[el]; });
      return mean;
    }

    function describeRockSalt(cations, options) {
      var opts = options || {};
      var spin = opts.spin || "high";
      var norm = oxideNormalizeSite(cations);
      var warnings = [];
      var solved = oxideAssignStates(norm, 2.0, opts.states || null, null);
      solved.warnings.forEach(function (w) { warnings.push(w); });
      var radii = oxideRadiiFor(norm, solved.states, 6, spin, warnings);
      var sFormula = oxideSublatticeEntropy({ M: norm }, { M: 1.0 }, "formula");
      var chi = oxideChiStats(norm, warnings);
      return {
        family: "rock_salt",
        sites: { M: norm },
        oxygen_per_formula_unit: 1.0,
        oxidation_states: solved.states,
        coordination: { M: 6 },
        shannon_radii: radii,
        descriptors: {
          s_config: sFormula,
          s_config_per_cation: sFormula,
          s_config_per_site: { M: sFormula },
          delta_r: oxideSizeDisorder(norm, radii),
          mean_radius: oxideMeanRadius(norm, radii),
          mean_chi: chi.mean,
          delta_chi: chi.delta
        },
        verdicts: { entropy: oxideEntropyVerdict(sFormula) },
        warnings: warnings
      };
    }

    function describeFluorite(cations, options) {
      var opts = options || {};
      var spin = opts.spin || "high";
      var oxygen = opts.oxygen === undefined || opts.oxygen === null ? 2.0 : Number(opts.oxygen);
      var norm = oxideNormalizeSite(cations);
      var warnings = [];
      var solved = oxideAssignStates(norm, 2.0 * oxygen, opts.states || null, null);
      solved.warnings.forEach(function (w) { warnings.push(w); });
      var radii = oxideRadiiFor(norm, solved.states, 8, spin, warnings);
      var sFormula = oxideSublatticeEntropy({ M: norm }, { M: 1.0 }, "formula");

      var sigma = null;
      var sigmaVerdict = null;
      var symbols = Object.keys(norm);
      if (symbols.length >= 2) {
        var fracs = symbols.map(function (el) { return norm[el]; });
        if (Math.max.apply(null, fracs) - Math.min.apply(null, fracs) > 1e-9) {
          warnings.push(
            "the fluorite radius-dispersion criterion is calibrated on equimolar " +
            "compositions; this composition is not equimolar"
          );
        }
        sigma = oxideRadiusSampleStd(symbols.map(function (el) { return radii[el]; }));
        sigmaVerdict = sigma > 0.095 ? "fluorite" : "bixbyite-or-multiphase";
      } else {
        warnings.push("the fluorite radius-dispersion criterion needs at least two cations");
      }

      var chi = oxideChiStats(norm, warnings);
      return {
        family: "fluorite",
        sites: { M: norm },
        oxygen_per_formula_unit: oxygen,
        oxidation_states: solved.states,
        coordination: { M: 8 },
        shannon_radii: radii,
        descriptors: {
          s_config: sFormula,
          s_config_per_cation: sFormula,
          s_config_per_site: { M: sFormula },
          delta_r: oxideSizeDisorder(norm, radii),
          mean_radius: oxideMeanRadius(norm, radii),
          radius_sigma: sigma,
          mean_chi: chi.mean,
          delta_chi: chi.delta
        },
        verdicts: {
          entropy: oxideEntropyVerdict(sFormula),
          spiridigliozzi: sigmaVerdict
        },
        warnings: warnings
      };
    }

    function oxideTwoSiteReport(family, aSite, bSite, siteMultiplicity, oxygen, cnA, cnB, states, spin) {
      var normA = oxideNormalizeSite(aSite);
      var normB = oxideNormalizeSite(bSite);
      var shared = Object.keys(normA).filter(function (el) {
        return Object.prototype.hasOwnProperty.call(normB, el);
      }).sort();
      if (shared.length) {
        throw new Error(
          shared.join(", ") + " appears on both sublattices; site-resolved oxidation " +
          "states are not supported — describe the sites separately"
        );
      }
      var warnings = [];
      var moles = {};
      Object.keys(normA).forEach(function (el) { moles[el] = normA[el] * siteMultiplicity; });
      Object.keys(normB).forEach(function (el) { moles[el] = normB[el] * siteMultiplicity; });
      var groups = {};
      Object.keys(normA).forEach(function (el) { groups[el] = "A"; });
      Object.keys(normB).forEach(function (el) { groups[el] = "B"; });
      var solved = oxideAssignStates(moles, 2.0 * oxygen, states || null, groups);
      solved.warnings.forEach(function (w) { warnings.push(w); });
      var radiiA = oxideRadiiFor(normA, solved.states, cnA, spin, warnings);
      var radiiB = oxideRadiiFor(normB, solved.states, cnB, spin, warnings);

      var mult = {};
      mult.A = siteMultiplicity;
      mult.B = siteMultiplicity;
      var sFormula = oxideSublatticeEntropy({ A: normA, B: normB }, mult, "formula");
      var sCation = sFormula / (2.0 * siteMultiplicity);
      var sSiteA = oxideSublatticeEntropy({ A: normA }, { A: 1.0 }, "formula");
      var sSiteB = oxideSublatticeEntropy({ B: normB }, { B: 1.0 }, "formula");
      var chi = oxideChiStats(moles, warnings);

      var deltaA = oxideSizeDisorder(normA, radiiA);
      var deltaB = oxideSizeDisorder(normB, radiiB);
      var allRadii = {};
      Object.keys(radiiA).forEach(function (el) { allRadii[el] = radiiA[el]; });
      Object.keys(radiiB).forEach(function (el) { allRadii[el] = radiiB[el]; });

      var report = {
        family: family,
        sites: { A: normA, B: normB },
        oxygen_per_formula_unit: oxygen,
        oxidation_states: solved.states,
        coordination: { A: cnA, B: cnB },
        shannon_radii: allRadii,
        descriptors: {
          s_config: sFormula,
          s_config_per_cation: sCation,
          s_config_per_site: { A: sSiteA, B: sSiteB },
          delta_r_a: deltaA,
          delta_r_b: deltaB,
          delta_r_star: oxideCombinedSizeDisorder([deltaA, deltaB]),
          mean_radius_a: oxideMeanRadius(normA, radiiA),
          mean_radius_b: oxideMeanRadius(normB, radiiB),
          mean_chi: chi.mean,
          delta_chi: chi.delta
        },
        verdicts: { entropy: oxideEntropyVerdict(Math.max(sSiteA, sSiteB)) },
        warnings: warnings
      };
      return { report: report, normA: normA, normB: normB, states: solved.states };
    }

    function describePerovskite(aSite, bSite, options) {
      var opts = options || {};
      var spin = opts.spin || "high";
      var tWindow = opts.tWindow || [0.92, 1.04];
      var built = oxideTwoSiteReport(
        "perovskite", aSite, bSite, 1.0, 3.0, 12, 6, opts.states || null, spin
      );
      var report = built.report;
      var d = report.descriptors;
      var nA = 0;
      Object.keys(built.normA).forEach(function (el) {
        nA += built.normA[el] * built.states[el];
      });
      var t = goldschmidtT(d.mean_radius_a, d.mean_radius_b);
      var mu = octahedralFactor(d.mean_radius_b);
      var tau = null;
      var tauVerdict = null;
      try {
        tau = bartelTau(d.mean_radius_a, d.mean_radius_b, nA);
        tauVerdict = tau < 4.18 ? "perovskite" : "nonperovskite";
      } catch (error) {
        report.warnings.push(error.message);
      }
      d.goldschmidt_t = t;
      d.octahedral_mu = mu;
      d.bartel_tau = tau;
      d.mean_n_a = nA;
      report.verdicts.goldschmidt = oxideWindowVerdict(t, tWindow[0], tWindow[1]);
      report.verdicts.octahedral = oxideWindowVerdict(mu, 0.414, 0.732);
      report.verdicts.bartel = tauVerdict;
      return report;
    }

    function describePyrochlore(aSite, bSite, options) {
      var opts = options || {};
      var spin = opts.spin || "high";
      var built = oxideTwoSiteReport(
        "pyrochlore", aSite, bSite, 2.0, 7.0, 8, 6, opts.states || null, spin
      );
      var report = built.report;
      var d = report.descriptors;
      var ratio = oxideRadiusRatio(d.mean_radius_a, d.mean_radius_b);
      var verdict;
      if (ratio < 1.46) {
        verdict = "defect-fluorite";
      } else if (ratio > 1.78) {
        verdict = "no-single-cubic-phase";
      } else {
        verdict = "pyrochlore";
      }
      d.radius_ratio = ratio;
      report.verdicts.radius_ratio = verdict;
      return report;
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
      SINGH_LAMBDA_SS: SINGH_LAMBDA_SS,
      SINGH_LAMBDA_IM: SINGH_LAMBDA_IM,
      WANG_GAMMA_THRESHOLD: WANG_GAMMA_THRESHOLD,
      ANDREOLI_FCC_MAX: ANDREOLI_FCC_MAX,
      ANDREOLI_BCC_MAX: ANDREOLI_BCC_MAX,
      SENKOV_K2: SENKOV_K2,
      TSAI_SIGMA_VEC_MIN: TSAI_SIGMA_VEC_MIN,
      TSAI_SIGMA_VEC_MAX: TSAI_SIGMA_VEC_MAX,
      SHEIKH_DUCTILE_VEC: SHEIKH_DUCTILE_VEC,
      SHEIKH_BRITTLE_VEC: SHEIKH_BRITTLE_VEC,
      ELEMENT_DATA: DEFAULT_ELEMENT_DATA,
      ELEMENT_MECHANICS: ELEMENT_MECHANICS,
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
      deltaChi: deltaChi,
      meanElectronegativity: meanElectronegativity,
      sExcess: sExcess,
      deltaGSs: deltaGSs,
      deltaGMax: deltaGMax,
      phiKing: phiKing,
      phiYe: phiYe,
      singhLambda: singhLambda,
      wangGamma: wangGamma,
      hElastic: hElastic,
      predictYehSmix: predictYehSmix,
      predictZhangDelta: predictZhangDelta,
      predictGuoVec: predictGuoVec,
      predictYangOmega: predictYangOmega,
      predictKingPhi: predictKingPhi,
      predictYePhi: predictYePhi,
      OXIDE_ELEMENT_DATA: OXIDE_ELEMENT_DATA,
      OXIDE_R: OXIDE_R,
      OXYGEN_RADIUS: OXYGEN_RADIUS,
      oxideShannonRadius: oxideShannonRadius,
      oxideAssignStates: oxideAssignStates,
      oxideNormalizeSite: oxideNormalizeSite,
      oxideSublatticeEntropy: oxideSublatticeEntropy,
      oxideSizeDisorder: oxideSizeDisorder,
      oxideRadiusSampleStd: oxideRadiusSampleStd,
      goldschmidtT: goldschmidtT,
      octahedralFactor: octahedralFactor,
      bartelTau: bartelTau,
      describeRockSalt: describeRockSalt,
      describeFluorite: describeFluorite,
      describePerovskite: describePerovskite,
      describePyrochlore: describePyrochlore
    };
  }
);