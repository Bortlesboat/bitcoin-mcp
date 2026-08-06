# bitcoin-mcp
<!-- mcp-name: io.github.Bortlesboat/bitcoin-mcp -->

Give any AI agent Bitcoin superpowers — fee intelligence, mempool analysis, and 50 tools backed by your Bitcoin node or compatible API.

[![PyPI](https://img.shields.io/pypi/v/bitcoin-mcp)](https://pypi.org/project/bitcoin-mcp/)
[![Downloads](https://img.shields.io/pypi/dm/bitcoin-mcp)](https://pypi.org/project/bitcoin-mcp/)
[![Tests](https://github.com/Bortlesboat/bitcoin-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/Bortlesboat/bitcoin-mcp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OpenSats](https://img.shields.io/badge/Support-OpenSats-F7931A)](https://opensats.org)

**50 standard tools** · **6 prompts** · **8 resources** · **Bitcoin Core or compatible API backend** · **MIT licensed**

> If bitcoin-mcp is useful to you, consider giving it a [star](https://github.com/Bortlesboat/bitcoin-mcp/stargazers) — it helps others discover the project.

```bash
pip install bitcoin-mcp
```

bitcoin-mcp needs a Bitcoin data backend. It auto-detects a local Bitcoin Core/Knots node from its cookie or RPC settings. Without a local node, set `SATOSHI_API_URL` to a compatible deployment.

> **Service status:** the public Satoshi API previously hosted at `bitcoinsapi.com` is paused and should not be treated as a working default. Use a local node or an explicitly configured compatible API.

## Quick Start

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "uvx",
      "args": ["bitcoin-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add bitcoin -- uvx bitcoin-mcp
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "uvx",
      "args": ["bitcoin-mcp"]
    }
  }
}
```

### VS Code

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "bitcoin": {
      "command": "uvx",
      "args": ["bitcoin-mcp"]
    }
  }
}
```

### Zed

Add to your Zed `settings.json` under `context_servers`:

```json
{
  "context_servers": {
    "bitcoin": {
      "command": "uvx",
      "args": ["bitcoin-mcp"]
    }
  }
}
```

See the [Zed MCP docs](https://zed.dev/docs/ai/mcp) for the current settings location and custom server flow.

### Docker

```bash
docker build -t bitcoin-mcp .
docker run -i bitcoin-mcp
```

Or with docker compose:

```bash
docker compose up
```

Pass environment variables to connect to a local Bitcoin Core node or a compatible API:

```bash
docker run -i -e BITCOIN_RPC_HOST=host.docker.internal -e BITCOIN_RPC_PORT=8332 bitcoin-mcp
# or
docker run -i -e SATOSHI_API_URL=https://your-api.example bitcoin-mcp
```

### Ask whether to send Bitcoin now

Use this as the first useful activation path after install:

> "I need to send a Bitcoin transaction today. Use bitcoin-mcp to decide whether to send now or wait, and show the fee rate you used."

Expected path:

1. The agent calls `get_fee_recommendation`.
2. The answer gives a clear send now or wait recommendation with fee rates in sat/vB.
3. If the backend is unavailable, configure a local node or set `SATOSHI_API_URL` before retrying.

After it works, Star this repo and share a short showcase with the prompt, tool call, and outcome so other Bitcoin agent builders can see the path.

## Agent Integration

For repos that need Bitcoin tools, add `bitcoin-mcp` to the agent's MCP config and configure one of its supported backends:

- Local Bitcoin Core/Knots RPC settings: `BITCOIN_RPC_HOST`, `BITCOIN_RPC_PORT`, and optional credentials or datadir
- Compatible remote API: `SATOSHI_API_URL` and, when required, `SATOSHI_API_KEY`
- Satoshi API source and integration reference: https://github.com/Bortlesboat/bitcoin-api/blob/main/docs/AGENT_INTEGRATION.md

Generated HTTP examples should use canonical Satoshi API `/api/v1` paths.

## Why bitcoin-mcp?

- **Fee intelligence that saves real money** — know the cheapest time to send, compare fee tiers, estimate exact costs before broadcasting
- **Backend choice** — use your own Bitcoin Core/Knots node or an explicitly configured compatible API
- **First Bitcoin MCP server on the [Anthropic Registry](https://registry.modelcontextprotocol.io)**

## Top Use Cases

Ask your AI agent:

| Prompt | What it does |
|--------|-------------|
| "What's the cheapest time to send Bitcoin today?" | Fee recommendation with savings breakdown |
| "Analyze the current mempool congestion" | Real-time mempool depth, fee tiers, pending tx count |
| "How much would I save waiting 6 blocks vs next block?" | Side-by-side fee comparison across confirmation targets |
| "Search for this transaction: abc123..." | Full transaction decode with inscription detection |
| "Give me a situation summary of Bitcoin right now" | Price, fees, mempool, mining, difficulty — one call |

## Full Tool Reference

<details>
<summary>All 50 standard tools by category</summary>

### Fee Intelligence
| Tool | Description |
|------|-------------|
| `get_fee_recommendation` | Optimal fee rate with urgency tiers and savings tips |
| `get_fee_estimates` | Fee estimates across all confirmation targets |
| `estimate_smart_fee` | Fee estimate for a specific confirmation target |
| `compare_fee_estimates` | Side-by-side comparison of fee sources |
| `estimate_transaction_cost` | Exact cost estimate for a transaction before sending |

### Blocks & Transactions
| Tool | Description |
|------|-------------|
| `analyze_block` | Deep analysis of any block by height or hash |
| `get_block_stats` | Statistical breakdown of a block |
| `get_block_count` | Current chain height |
| `compare_blocks` | Compare two blocks side by side |
| `search_blocks` | Search a range of blocks |
| `analyze_transaction` | Full transaction analysis with inscription detection |
| `decode_raw_transaction` | Decode a raw transaction hex |
| `send_raw_transaction` | Broadcast a signed transaction |
| `check_utxo` | Check if a UTXO is spent or unspent |

### Mempool
| Tool | Description |
|------|-------------|
| `analyze_mempool` | Full mempool analysis — depth, fees, congestion |
| `get_mempool_info` | Mempool size, bytes, fee floor |
| `get_mempool_entry` | Details for a specific unconfirmed transaction |
| `get_mempool_ancestors` | Ancestor chain for a mempool transaction |

### Mining
| Tool | Description |
|------|-------------|
| `get_mining_info` | Current mining difficulty, hashrate, block reward |
| `analyze_next_block` | Preview of the next block template |
| `get_mining_pool_rankings` | Top mining pools by recent blocks |
| `get_difficulty_adjustment` | Time and percentage of next difficulty change |
| `get_halving_countdown` | Blocks and estimated time until next halving |

### Network & Status
| Tool | Description |
|------|-------------|
| `get_blockchain_info` | Chain state, verification progress, softfork status |
| `get_network_info` | Node version, connections, relay info |
| `get_node_status` | Connection status and node health |
| `get_peer_info` | Connected peer details |
| `get_chain_tips` | Active and stale chain tips |
| `get_chain_tx_stats` | Transaction throughput over N blocks |
| `get_utxo_set_info` | UTXO set size and total supply |
| `get_supply_info` | Circulating supply, inflation rate, percent mined |
| `get_situation_summary` | Aggregated overview — price, fees, mempool, mining |
| `get_btc_price` | Current BTC/USD price |
| `get_market_sentiment` | Fear/greed index and market indicators |

### Address & UTXO
| Tool | Description |
|------|-------------|
| `get_address_utxos` | UTXOs for an address |
| `validate_address` | Validate and classify a Bitcoin address |

### Indexed Address (requires blockchain indexer)
| Tool | Description |
|------|-------------|
| `get_address_balance` | Total received/sent/balance, tx count, first/last seen |
| `get_address_history` | Paginated transaction history with net value change |
| `get_address_transactions` | Transaction history with per-transaction value details |
| `get_indexed_transaction` | Enriched tx with resolved input addresses + spent status |
| `get_indexer_status` | Sync progress, ETA, blocks/sec |

### Security
| Tool | Description |
|------|-------------|
| `analyze_psbt_security` | Security analysis of a Partially Signed Bitcoin Transaction |
| `explain_inscription_listing_security` | Security guide for ordinal inscription listings |

### Utility
| Tool | Description |
|------|-------------|
| `search_blockchain` | Universal search — address, txid, block hash, or height |
| `generate_keypair` | Generate a new Bitcoin keypair |
| `explain_script` | Decode and explain a Bitcoin script |
| `decode_bolt11_invoice` | Decode a Lightning Network BOLT11 invoice |
| `describe_rpc_command` | Help text for any Bitcoin Core RPC command |
| `list_rpc_commands` | List all available RPC commands |
| `decode_xpub` | Decode and inspect an extended public key |

### Optional Remote API Tool

`query_remote_api` is registered only when `SATOSHI_API_URL` is set and the `l402` extra is installed. It queries canonical `/api/v1` routes on that explicitly configured endpoint.

</details>

## Configuration

Configure either a local Bitcoin Core/Knots node or a compatible remote API. If neither is available, bitcoin-mcp exits its connection check with a setup error instead of silently selecting an unavailable public service.

### CLI Flags

`bitcoin-mcp` supports the following runtime flags:

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--transport` | `stdio`, `sse`, `streamable-http` | `stdio` | MCP transport to run |
| `--host` | hostname / IP | `127.0.0.1` for HTTP transports | Bind host for `sse` and `streamable-http` |
| `--port` | integer | `8000` for HTTP transports | Bind port for `sse` and `streamable-http` |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | Server log verbosity |

Example:

```bash
bitcoin-mcp --transport sse --host 127.0.0.1 --port 8000 --log-level DEBUG
```

| Variable | Description | Default |
|----------|-------------|---------|
| `BITCOIN_RPC_HOST` | Bitcoin Core RPC host | `127.0.0.1` |
| `BITCOIN_RPC_PORT` | Bitcoin Core RPC port | Auto by network |
| `BITCOIN_NETWORK` | `mainnet`, `testnet`, `signet`, or `regtest` | `mainnet` |
| `SATOSHI_API_URL` | Compatible Satoshi API base URL | None |
| `SATOSHI_API_KEY` | API key for authenticated access | None |

To connect to a local Bitcoin Core node:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "uvx",
      "args": ["bitcoin-mcp"],
      "env": {
        "BITCOIN_RPC_HOST": "127.0.0.1",
        "BITCOIN_RPC_PORT": "8332"
      }
    }
  }
}
```

## Prompts & Resources

**6 built-in prompts** for common workflows:
`analyze_fee_environment`, `investigate_transaction`, `monitor_mempool_fees`, `taproot_adoption_report`, `network_health_report`, `track_transaction`

**8 resources** for context injection:
`bitcoin://connection/status`, `bitcoin://node/status`, `bitcoin://fees/current`, `bitcoin://fees/history`, `bitcoin://mempool/snapshot`, `bitcoin://protocol/script-opcodes`, `bitcoin://protocol/address-types`, `bitcoin://protocol/sighash-types`

## Links

- [Satoshi API source](https://github.com/Bortlesboat/bitcoin-api) — optional compatible backend implementation (public hosted service currently paused)
- [Anthropic MCP Registry](https://registry.modelcontextprotocol.io) — `io.github.Bortlesboat/bitcoin-mcp`
- [PyPI](https://pypi.org/project/bitcoin-mcp/)
- [GitHub](https://github.com/Bortlesboat/bitcoin-mcp)
- [Full tool documentation](https://github.com/Bortlesboat/bitcoin-mcp#full-tool-reference)

## Examples

See the [examples/](examples/) folder for documented usage patterns:
- [Fee Analysis](examples/fee_analysis.py) — find optimal send timing
- [Mempool Monitor](examples/mempool_monitor.py) — track congestion
- [Transaction Investigation](examples/transaction_investigation.py) — decode and analyze transactions
- [Block Analysis](examples/block_analysis.py) — inspect and compare blocks

## Support This Project

bitcoin-mcp is free, open-source Bitcoin infrastructure. Support development through [OpenSats](https://opensats.org).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, including how to add new tools and the PR checklist.

Please report security vulnerabilities privately — see [SECURITY.md](SECURITY.md).

## About

bitcoin-mcp is created and maintained by [Andrew Barnes](https://github.com/Bortlesboat), bridging AI agents and Bitcoin infrastructure through the Model Context Protocol.

Related projects:
- [Satoshi API](https://github.com/Bortlesboat/bitcoin-api) — Bitcoin fee intelligence API, 108 endpoints, usable as a self-hosted compatible backend
- [ChainPulse](https://github.com/Bortlesboat/chainpulse) — AI-powered Bitcoin network intelligence CLI
- [BAIP-1](https://github.com/Bortlesboat/baip-python) — Bitcoin Agent Identity Protocol
- [bitcoin-fee-observatory](https://github.com/Bortlesboat/bitcoin-fee-observatory) — Fee market analytics dashboard

## License

[MIT](LICENSE)
