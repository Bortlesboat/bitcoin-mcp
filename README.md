# bitcoin-mcp

<!-- mcp-name: io.github.Bortlesboat/bitcoin-mcp -->

[![PyPI](https://img.shields.io/pypi/v/bitcoin-mcp)](https://pypi.org/project/bitcoin-mcp/)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-blue)](https://github.com/modelcontextprotocol/servers)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-63%20passed-brightgreen)](tests/)

MCP server for Bitcoin Core/Knots nodes. **35 tools, 6 prompts, 7 resources** for AI agents to query the blockchain, analyze mempool fee markets, decode transactions, broadcast transactions, decode Lightning invoices, inspect mining economics, and explore the protocol.

Runs against **your local node** — no API keys, no rate limits, no third-party dependencies.

**The first Bitcoin MCP server on the [official Anthropic MCP Registry](https://github.com/modelcontextprotocol/servers).**

## No Node? No Problem

Point at a hosted [Satoshi API](https://bitcoinsapi.com) instance instead of running your own node:

```bash
SATOSHI_API_URL=https://bitcoinsapi.com bitcoin-mcp
```

This adds a `query_remote_api` tool that proxies requests through the REST API, with optional L402 Lightning micropayments.

## 60-Second Quickstart

```bash
# 1. Install
pip install bitcoin-mcp

# 2. Add to Claude Desktop (claude_desktop_config.json)
{
  "mcpServers": {
    "bitcoin": { "command": "bitcoin-mcp" }
  }
}

# 3. Ask Claude: "What's the current Bitcoin fee environment?"
```

That's it. The server auto-detects your node via cookie authentication.

## Install

```bash
pip install bitcoin-mcp
```

### Configuration

Override with environment variables if needed:

```bash
BITCOIN_RPC_HOST=127.0.0.1
BITCOIN_RPC_PORT=8332
BITCOIN_RPC_USER=myuser
BITCOIN_RPC_PASSWORD=mypassword
BITCOIN_DATADIR=E:/
BITCOIN_NETWORK=mainnet          # mainnet (default) | testnet | signet | regtest
SATOSHI_API_URL=https://bitcoinsapi.com  # optional: use remote API instead of local node
```

## 35 Tools

### Node & Network (3)
| Tool | Description |
|------|-------------|
| `get_node_status` | Chain, height, sync progress, disk, connections, version |
| `get_peer_info` | Connected peer addresses, latency, services |
| `get_network_info` | Protocol version, relay fee, warnings |

### Blockchain & Blocks (6)
| Tool | Description |
|------|-------------|
| `analyze_block` | Full analysis: pool ID, SegWit/Taproot adoption, fee distribution |
| `get_blockchain_info` | Chain, difficulty, softforks, chain work |
| `get_block_stats` | Raw statistics: median fee, total output, subsidy |
| `get_chain_tx_stats` | Transaction rate over N blocks |
| `get_chain_tips` | Active chain, forks, and stale branches |
| `search_blocks` | Block stats for a range of heights (max 10) |

### Mempool (4)
| Tool | Description |
|------|-------------|
| `analyze_mempool` | Fee buckets, congestion level, next-block minimum fee |
| `get_mempool_entry` | Details of a specific unconfirmed tx |
| `get_mempool_info` | Quick stats: count, bytes, min relay fee |
| `get_mempool_ancestors` | Ancestor transactions for CPFP analysis |

### Transactions (4)
| Tool | Description |
|------|-------------|
| `analyze_transaction` | Full decode + inscription detection + fee analysis |
| `decode_raw_transaction` | Decode raw hex without input lookup |
| `send_raw_transaction` | Broadcast a signed transaction (with fee safety limit) |
| `check_utxo` | Check if a specific output is unspent |

### Fee Estimation (4)
| Tool | Description |
|------|-------------|
| `get_fee_estimates` | Rates for 1/3/6/25/144 block targets |
| `get_fee_recommendation` | Plain-English send/wait advice |
| `estimate_smart_fee` | Custom confirmation target |
| `compare_fee_estimates` | Side-by-side urgency labels + cost for 140vB tx |

### Mining (2)
| Tool | Description |
|------|-------------|
| `get_mining_info` | Difficulty, hashrate, block size |
| `analyze_next_block` | Block template: revenue, fee percentiles, top-fee txs |

### UTXO Set (2)
| Tool | Description |
|------|-------------|
| `get_utxo_set_info` | Total UTXOs, supply, disk size (slow: ~1-2 min) |
| `get_block_count` | Current block height (fast) |

### AI Developer Tools (8)
| Tool | Description |
|------|-------------|
| `describe_rpc_command` | Structured help for any RPC command |
| `list_rpc_commands` | All commands grouped by category |
| `search_blockchain` | Smart router: auto-detects txid, block hash/height, or address |
| `explain_script` | Decode script hex into readable opcodes |
| `get_address_utxos` | Scan UTXO set for an address |
| `validate_address` | Validate and classify address type (P2PKH/P2SH/P2WPKH/P2WSH/P2TR) |
| `get_difficulty_adjustment` | Epoch progress, estimated adjustment percentage |
| `compare_blocks` | Side-by-side block statistics comparison |

### Lightning (1)
| Tool | Description |
|------|-------------|
| `decode_bolt11_invoice` | Decode a BOLT11 Lightning invoice (no LN node needed) |

## 6 Agent Workflow Prompts

Pre-built multi-step analysis templates that agents can invoke:

| Prompt | Description |
|--------|-------------|
| `analyze_fee_environment` | Fee market analysis with send/wait recommendation |
| `investigate_transaction` | Deep-dive transaction investigation |
| `monitor_mempool_fees` | Watch for fee drops below threshold |
| `taproot_adoption_report` | P2TR adoption trends over recent blocks |
| `network_health_report` | Comprehensive network health assessment |
| `track_transaction` | Track a tx from mempool to confirmation |

## 7 Resources

Static data endpoints for AI agents:

- `bitcoin://node/status` — node summary
- `bitcoin://fees/current` — fee estimates
- `bitcoin://mempool/snapshot` — mempool analysis
- `bitcoin://connection/status` — connection status + troubleshooting hints
- `bitcoin://protocol/script-opcodes` — Bitcoin Script opcodes reference
- `bitcoin://protocol/address-types` — address type properties and BIPs
- `bitcoin://protocol/sighash-types` — signature hash types

## Example Configs

See [`examples/`](examples/) for ready-to-use config snippets:
- [Claude Desktop](examples/claude-desktop.json)
- [Claude Code](examples/claude-code.json)
- [Cursor](examples/cursor.json)
- [Windsurf](examples/windsurf.json)

## What Makes This Different

| Feature | bitcoin-mcp | Competitors |
|---------|------------|-------------|
| Official MCP Registry | **Yes** | No |
| Tools / Prompts / Resources | **35 / 6 / 7** | Fewer |
| Data source | Your local node | Third-party APIs |
| No-node fallback | Satoshi API remote | N/A |
| Mempool analysis | Fee bucketing, congestion, CPFP | Basic stats only |
| Inscription detection | Yes | No |
| Pool identification | Yes | No |
| SegWit/Taproot metrics | Yes | No |
| Next-block prediction | Yes | No |
| Agent workflow prompts | 6 built-in | None |
| Rate limits | None | API-dependent |
| Typed responses | Pydantic models | Raw JSON |

## CLI

```bash
bitcoin-mcp              # Start MCP server (default)
bitcoin-mcp --version    # Print version
bitcoin-mcp --check      # Test RPC connection and exit
```

## Requirements

- Python 3.10+
- Bitcoin Core or Bitcoin Knots with `server=1` in bitcoin.conf
- `txindex=1` recommended for transaction lookups

## Related

- [Satoshi API](https://github.com/Bortlesboat/bitcoin-api) — REST API for Bitcoin nodes (pairs with bitcoin-mcp for remote access)
- [bitcoinlib-rpc](https://github.com/Bortlesboat/bitcoinlib-rpc) — the Python library powering this server
- [Bitcoin Protocol Guide](https://bortlesboat.github.io/bitcoin-protocol-guide/) — educational companion

## License

MIT
