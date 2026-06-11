# %% [markdown]
# # Example 1 — The Cantor alloy, end to end
#
# This notebook walks through every descriptor and every empirical
# rule in `hea-bench`, using the canonical equimolar CoCrFeMnNi
# (Cantor) alloy. By the end you will have:
#
# 1. Parsed a composition formula
# 2. Computed the core descriptors (ΔS_mix, δ, VEC, T_m, ΔH_mix, Ω,
#    Δχ, χ̄)
# 3. Computed the phi-family descriptors (S_E, ΔG_ss, ΔG_max,
#    King Φ, Ye φ)
# 4. Applied all six canonical phase-prediction rules
# 5. Compared the predictions to the experimental observation
#
# Cantor is the field's standard reference HEA, so every value below
# is also pinned in the test suite as ground truth. For the
# high-entropy-oxide side of the library, see example 02.

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
# `parse_formula` handles the common formula conventions
# (space-separated proportional amounts, packed compact form, and
# bare element strings) and always returns a normalized
# mole-fraction dict.

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
# ## Computing the core descriptors

# %%
print(f"  Cantor descriptors")
print(f"  --------------------------------------------")
print(f"  ΔS_mix  =  {hea_bench.smix(cantor):7.4f}  J / (mol·K)   = R · ln 5")
print(f"  δ       =  {hea_bench.delta(cantor):7.4f}  %  atomic-size mismatch")
print(f"  VEC     =  {hea_bench.vec(cantor):7.4f}     valence electrons")
print(f"  T_m     =  {hea_bench.melting_temperature(cantor):7.2f}  K   composition-weighted ROM")
print(f"  ΔH_mix  =  {hea_bench.mixing_enthalpy(cantor):7.4f}  kJ/mol   Miedema 4·c_i·c_j·H^pair")
print(f"  Ω       =  {hea_bench.omega(cantor):7.4f}     T_m·ΔS_mix / |ΔH_mix|")
print(f"  Δχ      =  {hea_bench.delta_chi(cantor):7.4f}     Pauling electronegativity mismatch")
print(f"  χ̄       =  {hea_bench.mean_electronegativity(cantor):7.4f}     mean Pauling electronegativity")

# %% [markdown]
# ## Computing the phi-family descriptors
#
# Two further descriptors compare competing
# thermodynamic terms. King capital Φ asks whether the disordered
# solid solution beats the most stable competing binary
# intermetallic. Ye lowercase φ asks whether the configurational
# entropy beats the enthalpic-plus-mismatch penalty, where the
# mismatch term is the Mansoori hard-sphere excess entropy `S_E`.

# %%
print(f"  Cantor phi-family descriptors")
print(f"  --------------------------------------------")
print(f"  S_E       =  {hea_bench.s_excess(cantor):8.4f}  J/(mol·K)  Mansoori excess entropy")
print(f"  ΔG_ss     =  {hea_bench.delta_g_ss(cantor):8.4f}  kJ/mol     Gibbs energy of disordered SS at T_m")
print(f"  ΔG_max    =  {hea_bench.delta_g_max(cantor):8.4f}  kJ/mol     most-negative binary pair enthalpy")
print(f"  Φ (King)  =  {hea_bench.phi_king(cantor):8.4f}              ΔG_ss / -|ΔG_max|")
print(f"  φ (Ye)    =  {hea_bench.phi_ye(cantor):8.4f}              (ΔS_mix - |ΔH_mix|/T_m) / |S_E|")

# %% [markdown]
# ## Applying the six canonical phase-prediction rules

# %%
from hea_bench.rules import yeh_smix, zhang_delta, guo_vec, yang_omega
from hea_bench.rules import king_phi, ye_phi

print(f"  Cantor — empirical rule predictions")
print(f"  --------------------------------------------")
print(f"  Yeh ΔS_mix bin     :  {yeh_smix.predict(cantor)}")
print(f"  Zhang δ < 6.5%     :  {zhang_delta.predict(cantor)}")
print(f"  Guo–Liu VEC        :  {guo_vec.predict(cantor)}")
print(f"  Yang Ω > 1.1       :  {yang_omega.predict(cantor)}")
print(f"  King Φ > 1.0       :  {king_phi.predict(cantor)}")
print(f"  Ye φ > 20.0        :  {ye_phi.predict(cantor)}")

# %% [markdown]
# ## What the rules actually predict
#
# All six rules agree: Cantor is **HEA-class, single-phase, FCC,
# solid-solution**. Experimentally, CoCrFeMnNi is indeed a single-phase
# FCC solid solution at high temperature — this is the famous original
# observation by Cantor *et al.* (2004) and Yeh *et al.* (2004) that
# launched the field. So all six rules score correctly on this one.
#
# The rules are simple empirical surrogates: a clean call on the Cantor
# alloy is not a guarantee they generalise. Treat them as fast screens,
# not predictions.
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
# Every descriptor and rule shown here is also available in the browser
# and desktop apps, which add the Miedema formation-enthalpy
# decompositions. For high-entropy oxides (rock salt, perovskite,
# fluorite, and pyrochlore formability descriptors over Shannon ionic
# radii), continue with example 02. See the project README for the
# full surface.
