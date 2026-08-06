# bitcoin-mcp Copilot Instructions

`bitcoin-mcp` gives MCP-compatible agents Bitcoin tools backed by a local Bitcoin node or an explicitly configured compatible API.

## Rules

- Tools must work against both local Bitcoin Core/Knots and explicitly configured Satoshi API-compatible backends.
- Keep tool docstrings clear because they appear directly in MCP client UIs.
- Preserve stable tool signatures unless making a major-version change.
- Keep Satoshi API-compatible paths canonical and versioned (`/api/v1`).
- Do not commit API keys, registry tokens, wallet material, or local node credentials.

## Satoshi API Reference

- Source: https://github.com/Bortlesboat/bitcoin-api
- Agent integration guide: https://github.com/Bortlesboat/bitcoin-api/blob/main/docs/AGENT_INTEGRATION.md

The former public deployment at bitcoinsapi.com is paused. Do not describe it as an available default or direct users to its signup and x402 routes.

## Verification

```bash
python -m pytest tests/ -q
```
