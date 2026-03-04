# bitcoin-mcp

MCP server for Bitcoin Core/Knots nodes. 20 tools for AI agents to query the blockchain, analyze mempool fee markets, decode transactions, and inspect mining economics.

Runs against **your local node** — no API keys, no rate limits, no third-party dependencies.

## Install

```bash
pip install bitcoin-mcp
```

## Quick Start

### With Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "bitcoin-mcp"
    }
  }
}
```

### With Claude Code

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "bitcoin-mcp"
    }
  }
}
```

### Configuration

The server auto-detects your node via cookie authentication. Override with environment variables:

```bash
BITCOIN_RPC_HOST=127.0.0.1
BITCOIN_RPC_PORT=8332
BITCOIN_RPC_USER=myuser
BITCOIN_RPC_PASSWORD=mypassword
BITCOIN_DATADIR=E:/
```

## 20 Tools

### Node & Network
| Tool | Description |
|------|-------------|
| `get_node_status` | Chain, height, sync progress, disk, connections, version |
| `get_peer_info` | Connected peer addresses, latency, services |
| `get_network_info` | Protocol version, relay fee, warnings |

### Blockchain & Blocks
| Tool | Description |
|------|-------------|
| `analyze_block` | Full analysis: pool ID, SegWit/Taproot adoption, fee distribution |
| `get_blockchain_info` | Chain, difficulty, softforks, chain work |
| `get_block_stats` | Raw statistics: median fee, total output, subsidy |
| `get_chain_tx_stats` | Transaction rate over N blocks |

### Mempool
| Tool | Description |
|------|-------------|
| `analyze_mempool` | Fee buckets, congestion level, next-block minimum fee |
| `get_mempool_entry` | Details of a specific unconfirmed tx |
| `get_mempool_info` | Quick stats: count, bytes, min relay fee |

### Transactions
| Tool | Description |
|------|-------------|
| `analyze_transaction` | Full decode + inscription detection + fee analysis |
| `decode_raw_transaction` | Decode raw hex without input lookup |
| `check_utxo` | Check if a specific output is unspent |

### Fee Estimation
| Tool | Description |
|------|-------------|
| `get_fee_estimates` | Rates for 1/3/6/25/144 block targets |
| `get_fee_recommendation` | Plain-English send/wait advice |
| `estimate_smart_fee` | Custom confirmation target |

### Mining
| Tool | Description |
|------|-------------|
| `get_mining_info` | Difficulty, hashrate, block size |
| `analyze_next_block` | Block template: revenue, fee percentiles, top-fee txs |

### UTXO Set
| Tool | Description |
|------|-------------|
| `get_utxo_set_info` | Total UTXOs, supply, disk size (slow: ~1-2 min) |
| `get_block_count` | Current block height (fast) |

## Resources

AI agents can also read these as static data:

- `bitcoin://node/status` — node summary
- `bitcoin://fees/current` — fee estimates
- `bitcoin://mempool/snapshot` — mempool analysis

## What Makes This Different

| Feature | bitcoin-mcp | Competitors |
|---------|------------|-------------|
| Data source | Your local node | Third-party APIs |
| Mempool analysis | Fee bucketing, congestion | Basic stats only |
| Inscription detection | Yes | No |
| Pool identification | Yes | No |
| SegWit/Taproot metrics | Yes | No |
| Next-block prediction | Yes | No |
| Rate limits | None | API-dependent |
| Typed responses | Pydantic models | Raw JSON |

## Requirements

- Python 3.10+
- Bitcoin Core or Bitcoin Knots with `server=1` in bitcoin.conf
- `txindex=1` recommended for transaction lookups

## Related

- [bitcoinlib-rpc](https://github.com/Bortlesboat/bitcoinlib-rpc) — the Python library powering this server
- [Bitcoin Protocol Guide](https://bortlesboat.github.io/bitcoin-protocol-guide/) — educational companion

## License

MIT
