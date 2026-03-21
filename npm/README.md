# bitcoin-mcp

npm wrapper for [bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp) -- the most comprehensive Bitcoin MCP server. 49 tools for AI agents, zero config.

This package is a thin Node.js wrapper that launches the Python `bitcoin-mcp` server via `uvx` or `pipx`.

## Quick Start

```bash
npx @bortlesboat/bitcoin-mcp
```

## Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "npx",
      "args": ["-y", "@bortlesboat/bitcoin-mcp"]
    }
  }
}
```

## Prerequisites

Requires one of:

- [uv](https://docs.astral.sh/uv/) (recommended) -- provides `uvx`
- [pipx](https://pypa.github.io/pipx/)

## Full Documentation

See the main repository for complete docs, tool list, and configuration options:

https://github.com/Bortlesboat/bitcoin-mcp
