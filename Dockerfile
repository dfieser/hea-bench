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
# The consolidated corpus is not shipped with the package, for the
# licensing reasons set out in the corpus card, so corpus_query and
# corpus_describe need a built corpus mounted and pointed at:
#
#   docker run --rm -i -v /path/to/corpus:/corpus \
#     -e HEA_BENCH_BENCHMARK_DIR=/corpus hea-bench-mcp
#
# The other eleven tools are self-contained. The descriptor core vendors
# its own data tables, reaches no network, and writes nothing.

FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
# --prefix keeps the install relocatable so the runtime stage can take it
# whole without carrying pip, its wheel cache, or the build backend.
RUN pip install --no-cache-dir --prefix=/install ".[mcp]"

FROM python:3.12-slim
COPY --from=build /install /usr/local
# Every tool is read-only, so the server never needs to be root.
RUN useradd --create-home --uid 10001 app
USER app
ENV PYTHONUNBUFFERED=1
# stdio transport: the client speaks JSON-RPC over stdin and stdout, so
# the container must be run interactively (-i) and nothing else may be
# written to stdout.
ENTRYPOINT ["hea-bench-mcp"]
