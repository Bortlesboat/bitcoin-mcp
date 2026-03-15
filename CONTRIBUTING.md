# Contributing to bitcoin-mcp

Thanks for your interest in contributing! bitcoin-mcp is the most comprehensive Bitcoin MCP server — 49 tools, 6 prompts, 7 resources, zero config. Every contribution makes AI agents smarter about Bitcoin.

## Quick Start

```bash
git clone https://github.com/Bortlesboat/bitcoin-mcp.git
cd bitcoin-mcp
pip install -e ".[dev]"
pytest
```

All tests pass without a Bitcoin node — everything is mocked.

## Where to Start

### Good first issues
Browse [issues labeled `good first issue`](https://github.com/Bortlesboat/bitcoin-mcp/issues?q=is%3Aopen+label%3A%22good+first+issue%22) — these are well-scoped with clear expected inputs/outputs and pointers to the relevant code.

### Help wanted
[`help wanted` issues](https://github.com/Bortlesboat/bitcoin-mcp/issues?q=is%3Aopen+label%3A%22help+wanted%22) are slightly more involved but still approachable. Read the issue description — it will tell you exactly which files to edit and what pattern to follow.

### Ideas welcome
Not sure what to build? Here are always-useful contributions:
- New tools that expose Bitcoin data AI agents frequently need
- Better error messages that help agents self-recover
- Test coverage for edge cases (invalid addresses, empty mempool, etc.)
- Usage examples in `examples/`

## Adding a New Tool

1. Find a similar tool in `src/bitcoin_mcp/server.py` and use it as a template
2. Add your tool with the `@mcp.tool()` decorator
3. Write a clear docstring — the LLM uses this to decide when to call your tool
4. Add at least 2 tests in `tests/test_server.py`
5. Update the tool count in `README.md` badges if your PR adds tools

### Tool design rules
- Return structured JSON, not prose
- Keep responses compact — no `indent=2` (saves LLM tokens)
- Cap large list responses (e.g., max 20 peers, max 50 transactions)
- Include an `error` key with a human-readable message on failures
- Tool descriptions should be specific enough that an LLM picks the right tool

### Example tool skeleton
```python
@mcp.tool()
async def get_something(param: str) -> str:
    """
    One sentence: what this tool does and when to use it.

    Args:
        param: What this parameter controls.

    Returns structured JSON with: field1, field2, ...
    """
    try:
        data = await _rpc("method", [param])
        return json.dumps({"result": data})
    except Exception as e:
        return json.dumps({"error": str(e)})
```

## Adding a Resource

Resources provide always-available context (no tool call needed). Use `@mcp.resource("bitcoin://category/name")`.

See existing resources near the bottom of `server.py` for examples.

## Guidelines

1. **One tool per PR** — easier to review and merge
2. **Tests required** — every new tool needs at least 2 tests (happy path + error case)
3. **No breaking changes** — don't rename existing tools or change their output schema
4. **Commit style** — `feat: add get_address_transactions tool` or `fix: handle empty mempool in analyze_mempool`

## Running Tests

```bash
pytest tests/ -v                    # all tests
pytest tests/ -k "test_fees" -v    # specific tests
pytest tests/ --tb=short           # compact output
```

## PR Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] New tool/resource has at least 2 tests
- [ ] README badge counts updated (if adding tools/resources/prompts)
- [ ] Docstring is clear and specific
- [ ] Response is compact JSON (no extra whitespace)

## Questions?

Open an issue or reach out at https://bitcoinsapi.com.
