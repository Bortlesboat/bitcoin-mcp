# bitcoin-mcp Copilot Instructions

`bitcoin-mcp` gives MCP-compatible agents Bitcoin tools and falls back to Satoshi API when no local Bitcoin node is configured.

## Rules

- Tools must work against both local Bitcoin Core/Knots and the hosted Satoshi API fallback.
- Keep tool docstrings clear because they appear directly in MCP client UIs.
- Preserve stable tool signatures unless making a major-version change.
- Keep Satoshi API fallback paths canonical and versioned (`/api/v1`).
- Do not commit API keys, registry tokens, wallet material, or local node credentials.

## Satoshi API Links

- Hosted API: https://bitcoinsapi.com
- API docs: https://bitcoinsapi.com/docs
- Agent overview: https://bitcoinsapi.com/llms.txt
- Agent integration guide: https://github.com/Bortlesboat/bitcoin-api/blob/main/docs/AGENT_INTEGRATION.md
- x402 first paid call: https://bitcoinsapi.com/x402/start

## Verification

```bash
python -m pytest tests/ -q
```
