# %% [markdown]
# # Example 1 — The Cantor alloy, end to end
#
# This notebook walks through every descriptor and every empirical
# rule in `hea-bench`, using the canonical equimolar CoCrFeMnNi
# (Cantor) alloy. By the end you will have:
#
# 1. Parsed a composition formula
# 2. Computed all six descriptors (ΔS_mix, δ, VEC, T_m, ΔH_mix, Ω)
# 3. Applied the four canonical phase-prediction rules
# 4. Compared the predictions to the experimental observation
#
# Cantor is the field's standard reference HEA, so every value below
# is also pinned in the test suite as ground truth.

# %% [markdown]
# ## Setup
#
# Top-level convenience imports make the most common functions
# directly available on the `hea_bench` namespace.

# %%
import hea_bench
print("hea_bench", hea_bench.__version__)

# %% [markdown]
# ## Parsing a composition
#
# `parse_formula` handles the three formula conventions used across
# the three source datasets (Borg's space-separated proportional
# amounts, Pei's packed compact form, and bare element strings) and
# always returns a normalized mole-fraction dict.

# %%
cantor = hea_bench.parse_formula("CoCrFeMnNi")
print("Cantor composition (normalized):")
for el, frac in sorted(cantor.items()):
    print(f"  {el}: {frac:.4f}")

# %% [markdown]
# Alternative ways to express the same alloy — all three parse to
# the same mole-fraction dict:

# %%
a = hea_bench.parse_formula("Co1Cr1Fe1Mn1Ni1")              # all unit coefficients
b = hea_bench.parse_formula("Co 1 Cr 1 Fe 1 Mn 1 Ni 1")     # Borg-style spaces
c = hea_bench.parse_formula("Co5Cr5Fe5Mn5Ni5")              # equimolar, any scale
print("a == b == c:", a == b == c)

# %% [markdown]
# ## Computing the six descriptors

# %%
print(f"  Cantor descriptors")
print(f"  --------------------------------------------")
print(f"  ΔS_mix  =  {hea_bench.smix(cantor):7.4f}  J / (mol·K)   = R · ln 5")
print(f"  δ       =  {hea_bench.delta(cantor):7.4f}  %  atomic-size mismatch")
print(f"  VEC     =  {hea_bench.vec(cantor):7.4f}     valence electrons")
print(f"  T_m     =  {hea_bench.melting_temperature(cantor):7.2f}  K   composition-weighted ROM")
print(f"  ΔH_mix  =  {hea_bench.mixing_enthalpy(cantor):7.4f}  kJ/mol   Miedema 4·c_i·c_j·H^pair")
print(f"  Ω       =  {hea_bench.omega(cantor):7.4f}     T_m·ΔS_mix / |ΔH_mix|")

# %% [markdown]
# ## Applying the four canonical phase-prediction rules

# %%
from hea_bench.rules import yeh_smix, zhang_delta, guo_vec, yang_omega

print(f"  Cantor — empirical rule predictions")
print(f"  --------------------------------------------")
print(f"  Yeh ΔS_mix bin     :  {yeh_smix.predict(cantor)}")
print(f"  Zhang δ < 6.5%     :  {zhang_delta.predict(cantor)}")
print(f"  Guo–Liu VEC        :  {guo_vec.predict(cantor)}")
print(f"  Yang Ω > 1.1       :  {yang_omega.predict(cantor)}")

# %% [markdown]
# ## What the rules actually predict
#
# All four rules agree: Cantor is **HEA-class, single-phase, FCC**.
# Experimentally, CoCrFeMnNi is indeed a single-phase FCC solid
# solution at high temperature — this is the famous original
# observation by Cantor *et al.* (2004) and Yeh *et al.* (2004) that
# launched the field. So all four rules score correctly on this one.
#
# That perfect-on-Cantor result is **not** representative of the
# rules' performance across the full benchmark; example 2 shows the
# headline numbers (Zhang δ ~ 57% accuracy, Yang Ω ~ 54%, etc.).
#
# ## A composition the rules disagree on
#
# Al-doped FeCoCrNi is a known "rule disagreement" alloy. At low Al
# the system stays FCC; with more Al it transitions through FCC+BCC
# duplex to fully BCC.

# %%
for al_frac in (0.1, 0.3, 0.5, 0.7, 1.0):
    comp = hea_bench.parse_formula(f"Al{al_frac} Co1 Cr1 Fe1 Ni1")
    print(
        f"  Al{al_frac:>4}CoCrFeNi:  "
        f"VEC={hea_bench.vec(comp):.2f}  "
        f"δ={hea_bench.delta(comp):.2f}%  "
        f"→ Guo-Liu says {guo_vec.predict(comp):>5}  "
        f"Zhang says {zhang_delta.predict(comp)}"
    )

# %% [markdown]
# As Al content rises, VEC falls (Al has only 3 valence electrons)
# and δ grows (Al is much larger than the 3d transition metals). The
# Guo–Liu rule eventually flips its prediction from FCC to mixed to
# BCC, which is qualitatively correct against the published
# experimental phase diagram for this system.
#
# ## Next steps
#
# Example 2 (`02_benchmark_evaluation.ipynb`) loads the consolidated
# v0.1.0 benchmark and runs all four rules across all 7,784
# compositions, producing the headline classifier statistics.
