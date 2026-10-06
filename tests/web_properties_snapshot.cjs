const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const core = require(path.join(repoRoot, "web", "hea-calculator-core.js"));
const cases = JSON.parse(
  fs.readFileSync(path.join(__dirname, "data", "web_properties_parity_cases.json"), "utf8")
);

const describe = {
  rock_salt_carbide: core.describeRockSaltCarbide,
  rock_salt_nitride: core.describeRockSaltNitride,
  diboride: core.describeDiboride,
};

const compositions = Object.keys(core.ELEMENT_DATA).map((el) => ({ [el]: 1 })).concat(cases.alloys);
process.stdout.write(
  JSON.stringify({
    properties: compositions.map((comp) => ({
      composition: comp,
      density: core.tierADensity(comp),
      cost_per_kg: core.costPerKg(comp),
      cost_breakdown: core.costBreakdown(comp),
    })),
    ceramics: cases.ceramics.map((c) => describe[c.structure](c.metals)),
    omega_sensitivity: cases.omega_sensitivity.map((c) => core.omegaSensitivity(c.composition, c.perturbation)),
  })
);
