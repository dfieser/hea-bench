"""Physical constants and shared thermodynamic defaults."""

R = 8.314  # J / (mol · K) ideal gas constant

# Phase 1b shared defaults for the v1.1 phi-family work.
KING_PHI_THRESHOLD = 1.0
YE_PHI_THRESHOLD = 20.0

# Packing fractions used by the Mansoori excess-entropy convention.
PACKING_FRACTION_BCC = 0.68
PACKING_FRACTION_FCC = 0.74
PACKING_FRACTION_AMORPHOUS = 0.64

# v2.1 Tier 0-2 criteria thresholds (primary sources in each module).
SINGH_LAMBDA_SS = 0.96      # Singh 2014: Lambda > 0.96 -> single disordered SS
SINGH_LAMBDA_IM = 0.24      # Lambda < 0.24 -> compounds dominate
WANG_GAMMA_THRESHOLD = 1.175  # Wang 2015: gamma < 1.175 -> SS packing feasible
ANDREOLI_FCC_MAX = 6.05     # kJ/mol; Andreoli 2019 fcc-SS window ceiling
ANDREOLI_BCC_MAX = 22.0     # kJ/mol; bcc-SS ceiling; above lies the glassy/IM band
SENKOV_K2 = 0.6             # Senkov-Miracle 2016: dS_IM = 0.6 * dS_mix assumption
TSAI_SIGMA_VEC_MIN = 6.88   # Tsai 2013 sigma window (Cr/V-containing alloys)
TSAI_SIGMA_VEC_MAX = 7.84
SHEIKH_DUCTILE_VEC = 4.5    # Sheikh 2016: VEC < 4.5 -> intrinsically ductile RHEA
SHEIKH_BRITTLE_VEC = 4.6    # VEC >= 4.6 -> brittle; between is borderline
