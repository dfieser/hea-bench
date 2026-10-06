"""Domain of applicability: is this composition inside what the corpus covers.

A prediction's interval says how uncertain the model is where its
assumptions hold; this module says whether the assumptions plausibly
hold at all. :func:`fit_domain` summarizes a corpus into a
:class:`DomainModel`, and :meth:`DomainModel.novelty` reports several
deliberately orthogonal signals for a query composition, because they
fail differently:

- ``element_set_seen`` and ``family_count``: is this exact element set
  in the corpus, and with how many compositions. Catches "new system"
  even when every element is common.
- ``nearest_family_distance``: minimum Jaccard distance between the
  query's element set and any corpus family. Catches "nothing even
  similar was ever made".
- ``descriptor_distance``: root-mean-square z-score of the query's 14
  matrix descriptors against the corpus cloud (scaled Euclidean,
  deliberately not Mahalanobis: a stdlib 14x14 inversion buys
  correlation-awareness at the price of numerical fragility, and this
  flag must never fail exotically). Catches "chemically plausible but
  physically far outside the data".
- ``element_coverage``: whether the descriptor tables cover every
  element at all.

``in_domain`` combines them with a conservative documented rule:
element coverage AND descriptor distance within the fitted threshold
(the 99th percentile of the corpus's own self-distances) AND nearest
family distance at most 0.5. It is a convenience; ship and read the
components. All signals describe this package's corpus coverage for
your query, nothing else.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from functools import cached_property, lru_cache

from ..composition import Composition, family_of, normalize
from ..descriptors.backend import NativeBackend, matrix_vector, scorable_elements

#: Jaccard distance above which a query family counts as far from every
#: corpus family. 0.5 means "less than half the union is shared with
#: anything ever made", a deliberately permissive bar; the distance
#: itself is in the output for stricter readings.
FAMILY_DISTANCE_THRESHOLD = 0.5

#: The self-distance quantile that becomes the descriptor-distance bar.
DISTANCE_QUANTILE = 0.99


@dataclass(frozen=True)
class DomainRow:
    """Minimal corpus-row adapter for :func:`fit_domain`.

    Lets any (composition, family) pair population — property training
    records, campaign observations — be summarized into a DomainModel
    without inventing a private adapter per caller.
    """

    composition: Composition
    family: str
    descriptor_ready: bool = True


@dataclass(frozen=True)
class DomainModel:
    """A corpus summarized for applicability queries; JSON-serializable."""

    corpus_version: str
    families: dict[str, int]
    descriptor_names: tuple[str, ...]
    mean: tuple[float, ...]
    scale: tuple[float, ...]
    distance_threshold: float
    covered: frozenset[str]
    n_fit_rows: int
    family_distance_threshold: float = FAMILY_DISTANCE_THRESHOLD

    @cached_property
    def _family_sets(self) -> tuple[frozenset[str], ...]:
        # Derived once per model: novelty() scans every corpus family per
        # query, and re-splitting ~1,300 keys per call dominated its cost.
        return tuple(frozenset(key.split("-")) for key in self.families)

    def _descriptor_distance(self, composition: Composition) -> float | None:
        values = NativeBackend().compute(composition)
        total = 0.0
        for name, mu, sigma in zip(self.descriptor_names, self.mean, self.scale):
            value = values.get(name)
            if value is None or not math.isfinite(value):
                return None
            total += ((value - mu) / sigma) ** 2
        return math.sqrt(total / len(self.descriptor_names))

    def novelty(self, composition: Composition) -> dict:
        """Orthogonal novelty signals plus the conservative in_domain rule."""
        comp = normalize(composition)
        present = frozenset(comp)
        family = family_of(comp)
        family_count = self.families.get(family, 0)
        nearest = min(
            (
                1.0 - len(present & other) / len(present | other)
                for other in self._family_sets
            ),
            default=1.0,
        )
        element_coverage = present <= self.covered
        descriptor_distance = self._descriptor_distance(comp) if element_coverage else None
        in_domain = (
            element_coverage
            and descriptor_distance is not None
            and descriptor_distance <= self.distance_threshold
            and nearest <= self.family_distance_threshold
        )
        return {
            "element_set_seen": family_count > 0,
            "family_count": family_count,
            "nearest_family_distance": nearest,
            "descriptor_distance": descriptor_distance,
            "descriptor_distance_threshold": self.distance_threshold,
            "family_distance_threshold": self.family_distance_threshold,
            "element_coverage": element_coverage,
            "in_domain": in_domain,
        }

    def to_json(self) -> str:
        return json.dumps(
            {
                "corpus_version": self.corpus_version,
                "families": self.families,
                "descriptor_names": list(self.descriptor_names),
                "mean": list(self.mean),
                "scale": list(self.scale),
                "distance_threshold": self.distance_threshold,
                "covered": sorted(self.covered),
                "n_fit_rows": self.n_fit_rows,
                "family_distance_threshold": self.family_distance_threshold,
            }
        )

    @classmethod
    def from_json(cls, text: str) -> "DomainModel":
        data = json.loads(text)
        return cls(
            corpus_version=data["corpus_version"],
            families=dict(data["families"]),
            descriptor_names=tuple(data["descriptor_names"]),
            mean=tuple(data["mean"]),
            scale=tuple(data["scale"]),
            distance_threshold=data["distance_threshold"],
            covered=frozenset(data["covered"]),
            n_fit_rows=data["n_fit_rows"],
            family_distance_threshold=data["family_distance_threshold"],
        )


def fit_domain(corpus) -> DomainModel:
    """Summarize a corpus (or iterable of corpus rows) into a DomainModel.

    Families are counted over every row. The descriptor cloud uses only
    rows whose elements the tables cover and whose 14 matrix descriptors
    are all finite, mirroring the benchmark's finite filter; the number
    of rows that survived is recorded as ``n_fit_rows``.

    Raises
    ------
    ValueError
        With fewer than two usable rows, since a spread cannot be
        estimated from one point.
    """
    rows = corpus.rows if hasattr(corpus, "rows") else tuple(corpus)
    version = getattr(corpus, "version", "custom")

    families: Counter = Counter(row.family for row in rows)

    backend = NativeBackend()
    names = backend.matrix_names()
    vectors: list[list[float]] = []
    for row in rows:
        if not row.descriptor_ready:
            continue
        vector = matrix_vector(row.composition, backend)
        if vector is not None:
            vectors.append(vector)

    if len(vectors) < 2:
        raise ValueError(
            f"need at least two descriptor-scorable rows to fit a domain model, "
            f"got {len(vectors)}"
        )

    count = len(vectors)
    mean = [sum(vector[i] for vector in vectors) / count for i in range(len(names))]
    scale = []
    for i in range(len(names)):
        variance = sum((vector[i] - mean[i]) ** 2 for vector in vectors) / (count - 1)
        deviation = math.sqrt(variance)
        # A descriptor constant across the corpus carries no distance
        # information; scale 1.0 makes any query deviation count raw
        # rather than dividing by zero.
        scale.append(deviation if deviation > 0 else 1.0)

    distances = sorted(
        math.sqrt(
            sum(((vector[i] - mean[i]) / scale[i]) ** 2 for i in range(len(names)))
            / len(names)
        )
        for vector in vectors
    )
    rank = min(count - 1, max(0, math.ceil(DISTANCE_QUANTILE * count) - 1))
    threshold = distances[rank]

    return DomainModel(
        corpus_version=version,
        families=dict(families),
        descriptor_names=names,
        mean=tuple(mean),
        scale=tuple(scale),
        distance_threshold=threshold,
        covered=scorable_elements(),
        n_fit_rows=count,
    )


@lru_cache(maxsize=1)
def default_domain() -> DomainModel | None:
    """The v0.1.0 phase-corpus domain model, or None outside a checkout.

    Fitted once per process (several seconds) and cached; the shared
    default for surfaces that want a corpus-coverage flag without
    managing their own DomainModel. None, never an exception, when the
    corpus is not built, so callers can degrade to a typed warning.
    """
    from .._model_cache import cached
    from ..corpus import load_corpus

    try:
        return cached("domain-v0.1.0", lambda: fit_domain(load_corpus(version="0.1.0")))
    except FileNotFoundError:
        return None


def novelty_score(composition: Composition, corpus) -> dict:
    """Convenience one-shot: fit a domain model and query it once.

    Refits from scratch on every call, which costs seconds on the full
    corpus; hold the :class:`DomainModel` from :func:`fit_domain` when
    querying repeatedly.
    """
    return fit_domain(corpus).novelty(composition)


__all__ = [
    "FAMILY_DISTANCE_THRESHOLD",
    "DomainModel",
    "default_domain",
    "fit_domain",
    "novelty_score",
]
