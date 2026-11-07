"""Physical constants and shared thermodynamic defaults."""

R = 8.314  # J / (mol · K) ideal gas constant

# Phase 1b shared defaults for the v1.1 phi-family work.
KING_PHI_THRESHOLD = 1.0
YE_PHI_THRESHOLD = 20.0

# Packing fractions used by the Mansoori excess-entropy convention.
PACKING_FRACTION_BCC = 0.68
PACKING_FRACTION_FCC = 0.74

# Singh Lambda, Wang gamma and the Andreoli elastic energy are values,
# not verdicts, in all four parts. Their published windows (Singh 0.96 /
# 0.24, Wang 1.175, Andreoli 6.05 / 22.0 kJ/mol) appear only as reference
# text, in the descriptor docstrings and the app, so no threshold constant
# exists for them anywhere.
SENKOV_K2 = 0.6             # Senkov-Miracle 2016: dS_IM = 0.6 * dS_mix assumption
TSAI_SIGMA_VEC_MIN = 6.88   # Tsai 2013 sigma window (Cr/V-containing alloys)
TSAI_SIGMA_VEC_MAX = 7.84
SHEIKH_DUCTILE_VEC = 4.5    # Sheikh 2016: VEC < 4.5 -> intrinsically ductile RHEA
SHEIKH_BRITTLE_VEC = 4.6    # VEC >= 4.6 -> brittle; between is borderline
