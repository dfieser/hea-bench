// Snapshot driver for the core's Miedema SS/amorphous/compound
// decomposition. Prints the full result object for a fixed set of
// compositions; tests/test_web_miedema.py pins the values.
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const core = require(path.join(repoRoot, "web", "hea-calculator-core.js"));

const CASES = {
  cantor: { elements: ["Co", "Cr", "Fe", "Mn", "Ni"], fractions: { Co: 0.2, Cr: 0.2, Fe: 0.2, Mn: 0.2, Ni: 0.2 } },
  al_cocrfeni: { elements: ["Al", "Co", "Cr", "Fe", "Ni"], fractions: { Al: 0.2, Co: 0.2, Cr: 0.2, Fe: 0.2, Ni: 0.2 } },
  cu_zr: { elements: ["Cu", "Zr"], fractions: { Cu: 0.5, Zr: 0.5 } },
  ti_al: { elements: ["Ti", "Al"], fractions: { Ti: 0.5, Al: 0.5 } },
  ni_si: { elements: ["Ni", "Si"], fractions: { Ni: 0.75, Si: 0.25 } },
  refractory: { elements: ["Hf", "Nb", "Ta", "Ti", "Zr"], fractions: { Hf: 0.2, Nb: 0.2, Ta: 0.2, Ti: 0.2, Zr: 0.2 } },
  // Bi has no Miedema row: exercises the missing-pair degradation.
  with_uncovered: { elements: ["Bi", "Co", "Ni"], fractions: { Bi: 0.2, Co: 0.4, Ni: 0.4 } },
};

const snapshot = { table_size: Object.keys(core.MIEDEMA_TABLE).length, cases: {} };
for (const [name, c] of Object.entries(CASES)) {
  snapshot.cases[name] = core.calculateMiedemaDescriptors(c.elements, c.fractions);
}
// One pair-level detail row so Gamma_AB itself is pinned, not only sums.
snapshot.cu_zr_details = core.computeMiedemaDetails("Cu", "Zr");

process.stdout.write(JSON.stringify(snapshot));
