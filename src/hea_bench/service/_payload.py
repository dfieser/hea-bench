"""What every service response shares: input parsing, the version stamp,
the citation keys and the caps on expensive calls."""

from __future__ import annotations

from .. import __version__
from .._json import strict_json
from ..composition import normalize, parse_formula

#: Citation keys -> short reference strings, returned by ``about()`` and
#: referenced by the per-value ``source`` fields.
SOURCES = {
    "Boltzmann": "Classical ideal configurational entropy, -R sum(c ln c).",
    "Zhang2008": "Zhang et al. (2008). Adv. Eng. Mater. 10, 534. delta rule.",
    "Guo2011": "Guo & Liu (2011). Prog. Nat. Sci. 21, 433. VEC rule.",
    "Yang2012": "Yang & Zhang (2012). Mater. Chem. Phys. 132, 233. Omega rule.",
    "Yeh2004": "Yeh et al. (2004). Adv. Eng. Mater. 6, 299. Entropy classes.",
    "King2016": "King et al. (2016). Acta Mater. 104, 172. Phi criterion.",
    "Ye2015": "Ye et al. (2015). Scripta Mater. 104, 53. phi criterion.",
    "Mansoori1971": "Mansoori et al. (1971). J. Chem. Phys. 54, 1523. Hard-sphere excess entropy.",
    "deBoer1988": "de Boer et al. (1988). Cohesion in Metals. Miedema parametrization.",
    "Takeuchi2005": "Takeuchi & Inoue (2005). Mater. Trans. 46, 2817. Pair-enthalpy table.",
    "Pauling": "Pauling electronegativities from the vendored element table.",
    "CRC": "Melting points (CRC Handbook) from the curated 55-element table.",
    "LA4003": "Teatum, Gschneidner & Waber (1968). LA-4003. CN12 metallic radii.",
    "MS2017": "Miracle & Senkov (2017). Acta Mater. 122, 448. Review. Table 3 cross-checks.",
    "Singh2014": "Singh et al. (2014). Intermetallics 53, 112. Lambda = S_mix/delta^2.",
    "Wang2015": "Wang et al. (2015). Scripta Mater. 94, 28. Solid-angle gamma.",
    "SenkovMiracle2016": "Senkov & Miracle (2016). J. Alloys Compd. 658, 603. k1 vs k1_cr(T).",
    "Andreoli2019": "Andreoli et al. (2019). Materialia 5, 100222. Elastic-strain energy.",
    "Tsai2013": "Tsai et al. (2013). Mater. Res. Lett. 1, 207. Sigma-phase VEC window.",
    "Sheikh2016": "Sheikh et al. (2016). J. Appl. Phys. 120, 164902. RHEA ductility VEC.",
    "Shannon1976": "Shannon (1976). Acta Cryst. A32, 751. Effective ionic radii.",
    "Goldschmidt1926": "Goldschmidt (1926). Naturwissenschaften 14, 477. Tolerance factor.",
    "Bartel2019": "Bartel et al. (2019). Sci. Adv. 5, eaav0693. tau factor.",
    "Spiridigliozzi2021": "Spiridigliozzi et al. (2021). Acta Mater. 202, 181. Fluorite sigma rule.",
    "Subramanian1983": "Subramanian et al. (1983). Prog. Solid State Chem. 15, 55. Pyrochlore window.",
    "ManchonGordon2025": "Manchon-Gordon et al. (2025). Materials 18, 3862. HEO descriptor windows.",
    "Rost2015": "Rost et al. (2015). Nat. Commun. 6, 8485. Entropy-stabilized oxides.",
}

#: Rows an MCP sample returns at most.
CORPUS_SAMPLE_CAP = 50
#: Largest dataset page the app may request in one call.
PAGE_CAP = 500
#: The design search caps, enforced before any work.
DESIGN_MAX_PALETTE = 10
DESIGN_MAX_CANDIDATES = 20
DESIGN_MIN_STEP = 0.05
DESIGN_BUDGET = 50_000
#: Largest campaign batch one call may ask for.
CAMPAIGN_MAX_BATCH = 10


def stamp(payload: dict) -> dict:
    """Attach the library version to a tool response, as strict JSON."""
    payload["hea_bench_version"] = __version__
    return strict_json(payload)


def parse(formula: str) -> dict[str, float]:
    """Parse a composition string (already normalized), with a structured error."""
    try:
        return dict(parse_formula(formula))
    except Exception as exc:
        raise ValueError(
            f"could not parse composition {formula!r}: {exc}. Use element "
            f"symbols with optional amounts, e.g. 'CoCrFeMnNi' or "
            f"'Co20Cu20Fe5Mn35Ni20' or 'Al0.3CoCrFeNi'."
        ) from None


def read_composition(value) -> dict[str, float]:
    """A formula string or a mole-fraction dict, normalized, in the app's wording."""
    if isinstance(value, str):
        try:
            return dict(parse_formula(value))
        except Exception as error:
            raise ValueError(
                f"could not read the composition {value!r}: {error}. Write element "
                f"symbols with optional amounts, for example CoCrFeMnNi or Al0.3CoCrFeNi."
            ) from None
    return dict(normalize(value))


def needs_corpus(exc: FileNotFoundError) -> ValueError:
    """The unbuilt-corpus error, pointing an MCP client at corpus_build."""
    return ValueError(f"{exc}\nFrom an MCP client, call the corpus_build tool once instead.")


def say(progress, message: str, fraction: float) -> None:
    """Report progress through an optional ``(message, fraction)`` callback."""
    if progress is not None:
        progress(message, float(fraction))
