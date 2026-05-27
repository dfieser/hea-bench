const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const corePath = path.join(repoRoot, "web", "hea-calculator-core.js");
const casesPath = path.join(__dirname, "data", "web_parity_cases.json");
const calculatorCore = require(corePath);
const parityCases = JSON.parse(fs.readFileSync(casesPath, "utf8"));

const snapshot = {};

for (const parityCase of parityCases) {
  const sharedOptions = {
    pairEnthalpyResolver: calculatorCore.browserPairEnthalpy,
  };
  if (parityCase.king_temperature !== undefined) {
    sharedOptions.kingTemperature = Number(parityCase.king_temperature);
  }
  const coreResult = calculatorCore.calculateDescriptors(parityCase.composition, sharedOptions);
  const browserMixResult = calculatorCore.calculateDescriptors(parityCase.composition, {
    ...sharedOptions,
    pairTable: {},
  });
  const descriptors = {
    ...coreResult.descriptors,
    Hmix: browserMixResult.descriptors.Hmix,
    Omega: browserMixResult.descriptors.Omega,
  };
  const warnings = [
    ...new Set([...(browserMixResult.warnings || []), ...(coreResult.warnings || [])]),
  ];
  snapshot[parityCase.name] = {
    descriptors,
    rules: calculatorCore.rulePredictionsFromDescriptors(descriptors, {
      kingThreshold: calculatorCore.KING_PHI_THRESHOLD,
      yeThreshold: calculatorCore.YE_PHI_THRESHOLD,
    }),
    warnings,
  };
}

process.stdout.write(
  JSON.stringify(snapshot, (key, value) => {
    if (typeof value === "number" && !Number.isFinite(value)) {
      return value > 0 ? "__Infinity__" : "__-Infinity__";
    }
    return value;
  })
);