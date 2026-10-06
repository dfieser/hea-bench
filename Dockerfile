# Container image for the hea-bench MCP server (stdio transport).
#
# Registries and directory listings build this image and start the
# server to check that it runs, so it is deliberately built from source
# rather than from PyPI: a green build proves this commit works, not
# just that some published version does.
#
#   docker build -t hea-bench-mcp .
#   docker run --rm -i hea-bench-mcp
#
# The corpus is built inside the container, once, by the corpus_build
# tool: it downloads the 6.4 MB Peivaste file, which declares no license
# and is never shipped in an image (see the corpus card). Mount a volume
# to keep the built corpus between runs:
#
#   docker run --rm -i -v hea-bench-data:/home/app/.local/share/hea-bench hea-bench-mcp
#
# or point HEA_BENCH_BENCHMARK_DIR at a corpus built elsewhere. Every
# other tool is self-contained: the package vendors its own data tables
# and reaches no network.

FROM python:3.13-slim AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
# The wheel bundles the openly licensed source datasets and the published
# baseline table (force-include in pyproject.toml); tools/preflight.py
# checks that every bundled file reaches this stage.
COPY data/raw ./data/raw
COPY docs/benchmark-baselines.json ./docs/
# --prefix keeps the install relocatable so the runtime stage can take it
# whole without carrying pip, its wheel cache, or the build backend.
RUN pip install --no-cache-dir --prefix=/install ".[mcp]"

FROM python:3.13-slim
COPY --from=build /install /usr/local
# The server writes only to the app user's own folders, so it never
# needs to be root.
RUN useradd --create-home --uid 10001 app
USER app
ENV PYTHONUNBUFFERED=1
# stdio transport: the client speaks JSON-RPC over stdin and stdout, so
# the container must be run interactively (-i) and nothing else may be
# written to stdout.
ENTRYPOINT ["hea-bench-mcp"]
