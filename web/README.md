# web/ — Pyodide browser frontend

The browser frontend for `hea-bench`. There is **no JavaScript
re-implementation** of any descriptor — this page loads the same Python
wheel that gets installed by `pip install hea-bench`, runs it inside a
WebAssembly Python runtime (Pyodide), and exposes a thin UI over it.

## Architecture

```
                    ┌────────────────────────────────────────┐
                    │  user's browser tab                    │
                    │                                        │
   index.html ──────► Pyodide (Python 3.12 in WASM)          │
                    │      └── micropip.install(             │
                    │              "./dist/hea_bench-…whl")  │
                    │            └── from hea_bench…         │
                    │                  import smix(...)      │
                    └────────────────────────────────────────┘
```

One implementation. No server.

## Running locally

```bash
# from the hea-bench/ project root
python -m pip wheel . --no-deps -w web/dist   # rebuild after Python changes
cd web
python -m http.server 8000
# open http://localhost:8000
```

First load downloads the Pyodide runtime (~10 MB compressed) from
jsdelivr. Subsequent visits are cached.

## What's here

- `index.html` — the page. Loads Pyodide from CDN, installs the local
  wheel via `micropip`, and exposes a single demo descriptor
  (ΔS<sub>mix</sub>) as proof of the architecture.
- `dist/hea_bench-<version>-py3-none-any.whl` — the same wheel `pip`
  would install, served from a relative URL so the browser can fetch it.

## What's not here yet

Full descriptor set (δ, VEC, Ω, Miedema ΔH<sub>mix</sub>) — lands in
Phase 2. Consolidated benchmark dataset — lands in Phase 1. See
`../../PROJECT_PLAN.md`.

## Updating the wheel

Anytime the Python library changes:

```bash
python -m pip wheel . --no-deps -w web/dist
# delete older wheels in web/dist/ if you want a clean directory
```

The HTML page hard-codes the wheel filename, so bump the version in
`pyproject.toml` and update the filename in `index.html` for any release.
