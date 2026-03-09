# Contributing to bitcoin-mcp

Thanks for your interest in contributing! This project aims to be the best Bitcoin MCP server for AI agents.

## Quick Start

```bash
git clone https://github.com/Bortlesboat/bitcoin-mcp.git
cd bitcoin-mcp
pip install -e ".[dev]"
pytest
```

## What We Need

- **New tools** — see [open issues](https://github.com/Bortlesboat/bitcoin-mcp/issues) for requested MCP tools
- **Bug reports** — if a tool returns unexpected data, please open an issue with the tool name and input
- **Documentation** — usage examples, integration guides, and recipes
- **Testing** — more test coverage, especially for edge cases

## Guidelines

1. **One tool per PR** for new MCP tools (easier to review)
2. **Include tests** — every new tool needs at least one test
3. **Keep responses compact** — no `indent=2` in JSON (saves LLM tokens)
4. **Match existing patterns** — look at similar tools in `server.py` for style
5. **Update counts** — if you add tools/prompts/resources, update README badges

## Tool Design Principles

- Tool descriptions should help the LLM pick the right tool
- Return structured JSON, not prose
- Include error hints that help agents self-recover
- Cap large responses (e.g., peer list limited to 20)

## Running Tests

```bash
pytest tests/ -v
```

Tests mock the Bitcoin RPC connection, so no node is needed.

## Questions?

Open an issue or reach out at https://bitcoinsapi.com.
