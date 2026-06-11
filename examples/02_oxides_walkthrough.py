# %% [markdown]
# # Example 2 — High-entropy oxides, end to end
#
# This notebook walks through the `hea_bench.oxides` module using the
# literature anchor compositions that are pinned in the test suite:
#
# 1. The rock-salt prototype (MgCoNiCuZn)O, the "J14" entropy-stabilized
#    oxide of Rost et al. (2015)
# 2. The single-phase high-entropy perovskites of Jiang et al. (2018)
# 3. The fluorite radius-dispersion rule of Spiridigliozzi et al. (2021)
# 4. The pyrochlore radius-ratio window
# 5. The oxidation-state solver and how to override it
#
# Oxides change the physics relative to alloys: descriptors are computed
# per sublattice over Shannon (1976) effective ionic radii instead of
# metallic radii, and charge neutrality against the oxygen sublattice is
# a hard constraint, solved explicitly before any radius is looked up.

# %% [markdown]
# ## Setup

# %%
from hea_bench import oxides
import hea_bench
print("hea_bench", hea_bench.__version__)

# %% [markdown]
# ## The rock-salt prototype: (MgCoNiCuZn)O
#
# Each `describe_*` function takes cation amounts (any scale; the site is
# normalized internally) and returns one dict with everything: the solved
# oxidation states, the Shannon radii actually used, the descriptors, the
# rule verdicts, and any warnings.

# %%
j14 = oxides.describe_rock_salt({"Mg": 1, "Co": 1, "Ni": 1, "Cu": 1, "Zn": 1})

print("  Oxidation states :", j14["oxidation_states"])
print("  Shannon radii (Å):", {el: round(r, 3) for el, r in j14["shannon_radii"].items()})
d = j14["descriptors"]
print(f"  ΔS_config        =  {d['s_config']:7.4f}  J/(mol·K)  = R·ln 5, the 1.61R of the HEO literature")
print(f"  δr               =  {d['delta_r']:7.4f}  %  cation size disorder")
print(f"  χ̄ / Δχ           =  {d['mean_chi']:.3f} / {d['delta_chi']:.4f}  Pauling")
print("  Verdicts         :", j14["verdicts"])

# %% [markdown]
# All five cations solve to 2+, the radii are the six-fold Shannon values
# (high-spin for Co), and the entropy lands exactly on R ln 5. The entropy
# verdict classifies on the most-disordered sublattice, which is the
# convention the HEO literature uses.
#
# ## Perovskites: tolerance factors
#
# Jiang et al. (2018) showed that the Goldschmidt tolerance factor, not
# the cation size difference, is what discriminates single-phase
# high-entropy perovskites. Their single-phase compositions cluster at
# t ≈ 0.98 to 1.02. The module reports the classical t, the octahedral
# factor μ, and the modern Bartel τ (perovskite predicted when τ < 4.18).

# %%
pvk = oxides.describe_perovskite(
    {"Sr": 1},
    {"Zr": 1, "Sn": 1, "Ti": 1, "Hf": 1, "Mn": 1},
)
d = pvk["descriptors"]
print("  Sr(Zr,Sn,Ti,Hf,Mn)O3 — single-phase cubic in Jiang 2018")
print(f"  B-site states :", {el: q for el, q in pvk['oxidation_states'].items() if el != 'Sr'})
print(f"  t   = {d['goldschmidt_t']:.4f}   (window 0.92–1.04)")
print(f"  μ   = {d['octahedral_mu']:.4f}   (window 0.414–0.732)")
print(f"  τ   = {d['bartel_tau']:.4f}   (perovskite if < 4.18)")
print(f"  ΔS  = {d['s_config_per_site']['B']:.3f} J/(mol·K) on the B sublattice (1.61R)")
print("  Verdicts:", pvk["verdicts"])

# %% [markdown]
# ## Fluorites: the radius-dispersion rule
#
# For equimolar rare-earth-based oxides, Spiridigliozzi et al. (2021,
# Acta Mater. 202, 181) found that a single-phase fluorite forms when the
# sample standard deviation of the eight-fold cation radii exceeds
# 0.095 Å; below that, bixbyite-type or mixed phases form instead. Their
# follow-up (Materials 16, 2219, 2023) also showed the fluorite
# transition temperature drops as the dispersion grows.
#
# Rare-earth fluorites are oxygen-deficient, so the oxygen content per
# formula unit is an input (1.7 for an equimolar 4+/3+ mix); the charge
# balance is solved against it.

# %%
samples = [
    ("(Ce,Zr,Nd,Y,Er)O1.7  published SD 0.0976", {"Ce": 1, "Zr": 1, "Nd": 1, "Y": 1, "Er": 1}, 1.7),
    ("(Ce,Zr,La,Y,Gd)O1.7  published SD 0.117 ", {"Ce": 1, "Zr": 1, "La": 1, "Y": 1, "Gd": 1}, 1.7),
    ("(Ce,Zr,La,Nd,Sm)O1.7 published SD 0.128 ", {"Ce": 1, "Zr": 1, "La": 1, "Nd": 1, "Sm": 1}, 1.7),
    ("(Ce,Zr,Hf,Sn,Ti)O2   Chen 2018 ESO      ", {"Ce": 1, "Zr": 1, "Hf": 1, "Sn": 1, "Ti": 1}, 2.0),
]
for label, cations, oxygen in samples:
    rep = oxides.describe_fluorite(cations, oxygen=oxygen)
    sigma = rep["descriptors"]["radius_sigma"]
    print(f"  {label}  σ = {sigma:.4f} Å  → {rep['verdicts']['spiridigliozzi']}")

# %% [markdown]
# The three rare-earth samples reproduce the published standard
# deviations to every quoted digit, which is an end-to-end check of the
# vendored radii and the convention (eight-fold radii, n−1 denominator).
# Chen's (Ce,Zr,Hf,Sn,Ti)O2 sits below the threshold: consistent with
# experiment, it only forms a single phase at very high temperature as a
# true entropy-stabilized oxide, multiphase at low temperature and
# reversible.
#
# ## Pyrochlores: the radius-ratio window
#
# A2B2O7 pyrochlores form for 1.46 < r(A)/r(B) < 1.78 (eight-fold A over
# six-fold B); below the window a defect fluorite forms instead. Walking
# the B site through Zr, Hf, Ti, and Sn shows the window in action for a
# five-RE A site.

# %%
a_site = {"La": 1, "Ce": 1, "Nd": 1, "Sm": 1, "Eu": 1}
for b in ("Zr", "Hf", "Ti", "Sn"):
    rep = oxides.describe_pyrochlore(a_site, {b: 1})
    ratio = rep["descriptors"]["radius_ratio"]
    print(f"  (5RE)2{b}2O7:  r(A)/r(B) = {ratio:.3f}  → {rep['verdicts']['radius_ratio']}")

# %% [markdown]
# ## The oxidation-state solver, and overriding it
#
# States are assigned by enumerating tabulated oxidation states and
# keeping the charge-neutral assignments, preferring common states and
# charge-uniform sublattices. When chemistry knowledge says otherwise,
# pass explicit states. La(Cr,Mn,Fe,Co,Ni)O3 is a good example: the
# default solution balances charge using only common states (mixed
# valence on the B site), while forcing the all-3+ assignment reaches
# for the less common Mn(III) and Ni(III).

# %%
default = oxides.describe_perovskite({"La": 1}, {"Cr": 1, "Mn": 1, "Fe": 1, "Co": 1, "Ni": 1})
print("  default :", {el: q for el, q in default["oxidation_states"].items() if el != "La"})

forced = oxides.describe_perovskite(
    {"La": 1},
    {"Cr": 1, "Mn": 1, "Fe": 1, "Co": 1, "Ni": 1},
    states={"Cr": [3], "Mn": [3], "Fe": [3], "Co": [3], "Ni": [3]},
)
print("  forced  :", {el: q for el, q in forced["oxidation_states"].items() if el != "La"})
print(f"  δr(B) default = {default['descriptors']['delta_r_b']:.3f} %")
print(f"  δr(B) all-3+  = {forced['descriptors']['delta_r_b']:.3f} %")

# %% [markdown]
# The size-disorder value changes with the assignment because every
# Shannon radius depends on the oxidation state. This is the main
# convention risk in oxide descriptors, which is why the report always
# shows the states and radii it used.
#
# Spin matters the same way for 3d cations. The module defaults to
# high-spin radii (appropriate at ceramic synthesis temperatures) and
# accepts `spin="low"`:

# %%
hs, _ = oxides.shannon_radius("Co", 3, 6, spin="high")
ls, _ = oxides.shannon_radius("Co", 3, 6, spin="low")
print(f"  Co3+ six-fold radius: high-spin {hs:.3f} Å, low-spin {ls:.3f} Å")

# %% [markdown]
# ## Caveats
#
# The verdicts are weak empirical screens calibrated on small literature
# datasets, exactly like the alloy-side rules. The fluorite criterion is
# calibrated on equimolar rare-earth-based oxides and the module warns
# when you leave that domain. Single-phase can mean entropy-stabilized,
# meaning stable only above a transition temperature and retained by
# quenching. Everything shown here is also available in the browser and
# desktop apps under the Oxides mode, computed by the same parity-tested
# core.
