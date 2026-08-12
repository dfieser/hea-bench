"""Indicative element prices in USD per kg, date-stamped and sourced.

These are order-of-magnitude screening numbers assembled 2026-08, never
quotes. Read the basis column before comparing rows: LME and bullion
rows are one-day snapshots of an unusually hot 2026 market; rows marked
"contained" price the element inside its common traded form
(ferroalloy, oxide, APT) rather than pure massive metal; rows marked
"oxide" have no liquid metal market at all, and reduction to metal
multiplies cost several-fold. Two-tier pricing from the 2024-2026
Chinese export controls means Western prices for Ga, Ge, In, Sb, Bi, W
and the magnet rare earths run roughly 2 to 4 times Chinese domestic
prices; where a tier had to be picked, the row says which. Research
quantities from chemical suppliers cost far more than any number here.

Rows with asof "2025" are USGS Mineral Commodity Summaries 2026 annual
averages for calendar 2025 (doi:10.3133/mcs2026); monthly asof values
are recent market quotes from the named source. Os is a nominal
benchmark for an essentially untraded market and Tm rests on a single
producer quote; both are flagged in their basis strings. Th and U are
contained values for compounds, not fabricated radioactive metal.

Each row: (usd_per_kg, basis, asof, source).
"""

from __future__ import annotations

#: symbol -> (usd_per_kg, basis, asof, source)
PRICES_USD_PER_KG: dict[str, tuple[float, str, str, str]] = {
    "Ag": (2130.0, "bullion spot", "2026-08", "Umicore precious-metal prices"),
    "Al": (3.4, "LME cash, 99.7% ingot", "2026-08", "LME via Westmetall"),
    "Au": (142000.0, "bullion spot", "2026-08", "Umicore precious-metal prices"),
    "Be": (1600.0, "contained in Cu-Be master alloy, US unit value", "2025", "USGS MCS 2026"),
    "Bi": (67.0, "99.99% metal, Western warehouse", "2026-08", "Strategic Metals Invest"),
    "Ca": (2.7, "98% reductive ingot, EXW China", "2026-07", "ScrapMonster minor metals"),
    "Ce": (4.1, "metal 99%, China domestic", "2026-08", "SMM relay (rare-earth-mining.com)"),
    "Co": (56.0, "metal benchmark", "2026-08", "Trading Economics cobalt"),
    "Cr": (13.0, "metal, US market (tariff-inflated vs China)", "2025", "USGS MCS 2026"),
    "Cu": (14.4, "LME cash, grade A", "2026-08", "LME via Westmetall"),
    "Dy": (930.0, "metal, Western warehouse", "2026-08", "Strategic Metals Invest"),
    "Er": (82.0, "oxide basis (Er2O3), China; no metal market", "2026-08",
           "SMM relay (rare-earth-mining.com)"),
    "Fe": (0.5, "pig iron ~95% Fe, FOB export; lab-grade Fe costs far more", "2026-07",
           "steelonthenet pig iron"),
    "Ga": (2270.0, "99.99% metal, Western market (China domestic ~4x lower)", "2026-08",
           "Strategic Metals Invest"),
    "Gd": (55.0, "metal 99.9%, China domestic", "2026-08", "SMM relay (rare-earth-mining.com)"),
    "Ge": (8600.0, "zone-refined metal, Western market", "2026-08", "Strategic Metals Invest"),
    "Hf": (3800.0, "unwrought metal (2026 merchant quotes run higher)", "2025", "USGS MCS 2026"),
    "Ho": (79.0, "oxide basis (Ho2O3), China; no metal market", "2026-08",
           "SMM relay (rare-earth-mining.com)"),
    "In": (970.0, "99.99% metal, Western warehouse", "2026-08", "Strategic Metals Invest"),
    "Ir": (254000.0, "spot", "2026-08", "Umicore precious-metal prices"),
    "La": (3.2, "metal 99%, China domestic", "2026-08", "SMM relay (rare-earth-mining.com)"),
    "Li": (140.0, "metal 99.9%, China", "2026-03", "ChemAnalyst lithium metal"),
    "Lu": (670.0, "oxide basis (Lu2O3), China; no metal market", "2026-08",
           "SMM relay (rare-earth-mining.com)"),
    "Mg": (2.5, "99.8% metal, European free market", "2025", "USGS MCS 2026"),
    "Mn": (2.3, "electrolytic metal 99.7%, China", "2026-07", "SMM relay (critical-minerals-news)"),
    "Mo": (51.0, "contained in molybdic oxide, US", "2025", "USGS MCS 2026"),
    "Nb": (40.0, "contained in ferroniobium (65% Nb)", "2025", "USGS MCS 2026"),
    "Nd": (245.0, "metal, Western warehouse (China domestic ~2.5x lower)", "2026-08",
           "Strategic Metals Invest"),
    "Ni": (16.6, "LME cash, class 1", "2026-08", "LME via Westmetall"),
    "Os": (12900.0, "nominal benchmark; essentially untraded", "2026-08", "Metalary osmium"),
    "Pb": (1.9, "LME cash", "2026-08", "LME via Westmetall"),
    "Pd": (44900.0, "spot", "2026-08", "Umicore precious-metal prices"),
    "Pr": (245.0, "metal, Western warehouse", "2026-08", "Strategic Metals Invest"),
    "Pt": (57700.0, "spot", "2026-08", "Umicore precious-metal prices"),
    "Re": (2600.0, "metal pellets 99.9%", "2025", "USGS MCS 2026"),
    "Rh": (280000.0, "spot", "2026-08", "Umicore precious-metal prices"),
    "Ru": (56300.0, "spot", "2026-08", "Umicore precious-metal prices"),
    "Sb": (52.0, "99.65% metal, Western warehouse", "2026-08", "Strategic Metals Invest"),
    "Sc": (5200.0, "metal ingot 99.999%, small lots", "2025", "USGS MCS 2026"),
    "Si": (2.9, "silicon metal 98.5%+, US market", "2025", "USGS MCS 2026"),
    "Sm": (9.8, "metal, industrial, China domestic", "2026-08",
           "SMM relay (rare-earth-mining.com)"),
    "Sn": (55.0, "LME cash, 99.85%", "2026-08", "LME via Westmetall"),
    "Sr": (11.0, "metal 99%, EXW China", "2026-07", "ScrapMonster minor metals"),
    "Ta": (500.0, "metal, US market", "2026-06", "IMARC tantalum index"),
    "Tb": (4030.0, "metal, Western warehouse", "2026-08", "Strategic Metals Invest"),
    "Th": (26.0, "contained in compounds, US import unit value; not metal", "2025",
           "USGS MCS 2026"),
    "Ti": (12.0, "sponge, US published price (tariff-inflated vs China)", "2025",
           "USGS MCS 2026"),
    "Tm": (180.0, "oxide basis (Tm2O3), single producer quote; weak market", "2026-03",
           "SMM relay (rare-earth-mining.com)"),
    "U": (225.0, "contained in U3O8 spot, natural U; not fabricated metal", "2026-08",
          "U3O8 spot trackers"),
    "V": (31.0, "contained in ferrovanadium, US", "2025", "USGS MCS 2026"),
    "W": (114.0, "contained in APT, China domestic (Western ~3x higher)", "2026-08",
          "SMM relay (critical-minerals-news)"),
    "Y": (40.0, "metal 99.9%", "2025", "USGS MCS 2026"),
    "Yb": (13.0, "oxide basis (Yb2O3), China; no metal market", "2026-08",
           "SMM relay (rare-earth-mining.com)"),
    "Zn": (3.8, "LME cash, SHG", "2026-08", "LME via Westmetall"),
    "Zr": (22.0, "sponge, ex-works China", "2025", "USGS MCS 2026"),
}

#: The as-of stamp for the table as a whole (assembly date).
PRICE_ASOF = "2026-08"

__all__ = ["PRICE_ASOF", "PRICES_USD_PER_KG"]
