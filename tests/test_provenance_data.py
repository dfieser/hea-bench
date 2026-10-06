"""Tests for the structured provenance registry (v2.1).

The registry is the single source of truth that the web app's Data
view and provenance drawer are generated from; these tests keep it
complete and honest.
"""

from hea_bench.descriptors.data.elemental import ELEMENTAL_DATA
from hea_bench.descriptors.data.provenance import (
    ELEMENT_SOURCES,
    PROPERTY_SOURCES,
    REFERENCES,
)


def test_every_element_has_sources() -> None:
    assert set(ELEMENT_SOURCES) == set(ELEMENTAL_DATA)


def test_every_reference_resolvable() -> None:
    """Each bibliography entry must carry a DOI or a URL."""
    for key, ref in REFERENCES.items():
        assert ref.title, key
        assert ref.year, key
        assert ref.doi or ref.url, f"{key} has neither doi nor url"


def test_property_columns_documented() -> None:
    assert set(PROPERTY_SOURCES) == {"radius_pm", "melting_K", "valence", "electronegativity"}
    for col, src in PROPERTY_SOURCES.items():
        assert src.source_keys, col
        assert all(k in REFERENCES for k in src.source_keys), col


def test_crosscheck_flags_are_recorded() -> None:
    """The known source disagreements are visible, not hidden."""
    assert ELEMENT_SOURCES["Tm"].crosscheck_radius_pm == 156.0
    assert "misprint" in ELEMENT_SOURCES["Tm"].crosscheck_note.lower()
    assert "2115" in ELEMENT_SOURCES["Th"].notes
    assert any("valence" in f.lower() or "vec" in f.lower() for f in ELEMENT_SOURCES["U"].flags)
    assert any("divalent" in f.lower() for f in ELEMENT_SOURCES["Yb"].flags)
    assert ELEMENT_SOURCES["Ge"].crosscheck_radius_pm is None  # Ge's 124 IS the M&S value
    assert "137.8" in ELEMENT_SOURCES["Ge"].notes


def test_descriptor_reference_keys_present() -> None:
    """Every descriptor/rule the app cites has its primary source."""
    needed = {
        "yeh2004", "zhang2008", "takeuchi2000", "guo2011vec", "guo2011pnsmi",
        "yang2012", "king2016", "ye2015phi", "takeuchi2005", "deboer1988",
        "miedema1980", "singh2014", "wang2015", "senkov2016", "andreoli2019",
        "tsai2013", "sheikh2016", "pickering2016", "la4003", "ms2017",
        "gschneidner1966", "matminer2018", "crc", "pauling1960", "mansoori1971",
    }
    missing = needed - set(REFERENCES)
    assert not missing, f"missing reference keys: {sorted(missing)}"


def test_app_integrity_hashes_match_the_library() -> None:
    """The Element data tab's file hashes are the ones the library reports."""
    import json
    import re
    from pathlib import Path

    from hea_bench.descriptors.elements import element_data

    index = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    block = re.search(r"const DATA_FILE_SHAS = (\{.*?\});", index, re.S).group(1)
    assert json.loads(block) == element_data(["Fe"])["data_files"], (
        "web/index.html DATA_FILE_SHAS is stale. Fix: PYTHONPATH=src python tests/data/_sync_js_provenance.py"
    )
