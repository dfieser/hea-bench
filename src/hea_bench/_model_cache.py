"""Fitted models, fitted once: in memory always, on disk when asked.

Every fit runs in a fresh context, so a ``custom_data`` block around the
first prediction can never leak custom elements or pair values into a
model that later calls reuse.

``HEA_BENCH_MODEL_CACHE`` names a folder where fitted models are kept
as compressed pickles, keyed by name, package version and scikit-learn
version. The app's engine sets it to a folder in the browser's
IndexedDB, so a returning visitor loads the models in about a second
instead of refitting them for about 18. Unset, nothing is written. A
file that fails to load is deleted and refit, never trusted.
"""

from __future__ import annotations

import contextvars
import gzip
import os
import pathlib
import pickle
import sys

from . import __version__

#: ``n_jobs`` for fitting the forests: every core in Python, one in the
#: browser engine, which has no worker processes. The trees come out the
#: same either way. Predictions stay on one thread, see :func:`serial`.
FOREST_JOBS = None if sys.platform == "emscripten" else -1


def serial(model):
    """``model``, set to predict on one thread.

    A forest predicting on several threads adds its trees' answers in the
    order the threads finish, so the same alloy could change in its last
    digit from one call to the next.
    """
    if getattr(model, "n_jobs", None) is not None:
        model.n_jobs = None
    return model


def cached(name: str, fit):
    """``fit()``'s result, from the cache folder when set and present."""
    folder = os.environ.get("HEA_BENCH_MODEL_CACHE")
    if not folder:
        return contextvars.Context().run(fit)
    import sklearn

    path = pathlib.Path(folder) / f"{name}-{__version__}-sklearn{sklearn.__version__}.pickle.gz"
    if path.exists():
        try:
            with gzip.open(path, "rb") as handle:
                return pickle.load(handle)
        except Exception:  # noqa: BLE001 - a torn or stale file is refit
            path.unlink(missing_ok=True)
    value = contextvars.Context().run(fit)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    with gzip.open(partial, "wb", compresslevel=1) as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(partial, path)
    return value
