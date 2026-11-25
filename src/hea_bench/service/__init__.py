"""The operations every surface shares, as plain JSON-shaped functions.

Internal, not public API: nothing here is exported, and the names may
change. The MCP tools in :mod:`hea_bench.mcp_server` and the engine
methods in :mod:`hea_bench.webapp` are thin wrappers over these
functions, so the two surfaces return the same numbers and cannot drift
apart. Each function takes plain values, such as formula strings and
dicts, and returns a dict that serializes as strict JSON. Nothing here
imports the MCP SDK or Pyodide, and nothing writes to a path the caller
names. ``ARCHITECTURE.md`` says what belongs in this layer.
"""

# Loaded here so the surfaces can write service.<module>.<function>.
from . import _payload as _payload
from . import alloys as alloys
from . import benchmark as benchmark
from . import dataset as dataset
from . import design as design
from . import predictions as predictions
