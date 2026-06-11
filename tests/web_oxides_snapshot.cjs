const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const corePath = path.join(repoRoot, "web", "hea-calculator-core.js");
const casesPath = path.join(__dirname, "data", "web_oxide_parity_cases.json");
const core = require(corePath);
const cases = JSON.parse(fs.readFileSync(casesPath, "utf8"));

const snapshot = {};

for (const c of cases) {
  const options = {};
  if (c.spin !== undefined) options.spin = c.spin;
  if (c.oxygen !== undefined) options.oxygen = c.oxygen;
  if (c.states !== undefined) options.states = c.states;

  let report;
  if (c.family === "rock_salt") {
    report = core.describeRockSalt(c.cations, options);
  } else if (c.family === "fluorite") {
    report = core.describeFluorite(c.cations, options);
  } else if (c.family === "perovskite") {
    report = core.describePerovskite(c.a_site, c.b_site, options);
  } else if (c.family === "pyrochlore") {
    report = core.describePyrochlore(c.a_site, c.b_site, options);
  } else {
    throw new Error("unknown family: " + c.family);
  }
  snapshot[c.name] = report;
}

process.stdout.write(JSON.stringify(snapshot));
