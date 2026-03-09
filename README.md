# bitcoin-mcp

<!-- mcp-name: io.github.Bortlesboat/bitcoin-mcp -->

[![PyPI](https://img.shields.io/pypi/v/bitcoin-mcp)](https://pypi.org/project/bitcoin-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-103%20passed-brightgreen)](tests/)
[![Tools](https://img.shields.io/badge/MCP%20tools-43-blue)]()
[![Install MCP Server](https://cursor.directory/deeplink/badge.svg)](https://cursor.directory/mcp-servers/bitcoin-mcp)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-blue)](https://github.com/modelcontextprotocol/servers)

> **Works with:** Claude Desktop · Cursor · VS Code · Windsurf · any MCP client

MCP server that lets AI agents **save money on Bitcoin fees and save time monitoring payments**. Your agent can check whether to send now or wait, verify when a payment confirms, and query any blockchain data — without you building custom Bitcoin plumbing.

Runs against **your local node** or the free hosted [Satoshi API](https://bitcoinsapi.com). No API keys needed, no rate limits, no third-party dependencies.

**The first Bitcoin MCP server on the [official Anthropic MCP Registry](https://github.com/modelcontextprotocol/servers).** 43 tools, 6 prompts, 7 resources.

## 60-Second Quickstart

```bash
# 1. Install
pip install bitcoin-mcp

# 2. Verify it works (auto-connects to hosted API if no local node):
bitcoin-mcp --check

# 3. Add to Claude Code:
claude mcp add bitcoin -s user -- bitcoin-mcp

# 4. Restart Claude Code, then ask: "Give me a Bitcoin briefing"
```

That's it. **Zero configuration required.** No local node, no API keys, no env vars.

bitcoin-mcp auto-detects your setup:
1. If you have Bitcoin Core/Knots running locally → uses your node
2. Otherwise → uses the free [Satoshi API](https://bitcoinsapi.com) automatically

### Advanced: Use Your Own Node

If you run Bitcoin Core or Bitcoin Knots locally, bitcoin-mcp auto-detects it (preferred over hosted API):

```bash
bitcoin-mcp --check      # shows "local node" or "Satoshi API"
```

## Install

```bash
pip install bitcoin-mcp
```

### Configuration

Everything works out of the box with no configuration. Override with environment variables only if needed:

```bash
# Override the hosted API URL (default: https://bitcoinsapi.com)
SATOSHI_API_URL=https://your-api.example.com

# Force local node connection (skips hosted API fallback)
BITCOIN_RPC_HOST=127.0.0.1
BITCOIN_RPC_PORT=8332
BITCOIN_RPC_USER=myuser
BITCOIN_RPC_PASSWORD=mypassword
BITCOIN_DATADIR=E:/
BITCOIN_NETWORK=mainnet                  # mainnet (default) | testnet | signet | regtest
```

### Docker

```bash
docker run bitcoin-mcp   # works out of the box — uses hosted API
```

## Recipes

Copy-paste these into Claude Desktop or Claude Code with bitcoin-mcp installed. Each one saves you money or time.

### "Give me a Bitcoin briefing"

> Give me a 30-second Bitcoin briefing: current price, fees, mempool congestion, and whether it's a good time to send.

Uses `get_situation_summary`. Returns BTC price, fee rates at 3 urgency levels, typical transaction cost in USD, and mempool state — all in one call.

### "How much will my transaction cost in dollars?"

> I want to send Bitcoin from 2 inputs to 2 outputs, all native SegWit. How much will the fee be in dollars at each urgency level?

Uses `estimate_transaction_cost`. Calculates exact vsize for your transaction shape, multiplies by current fee rates, converts to USD. Shows how much you save by waiting.

### "Should I send Bitcoin right now?"

> What's the current fee environment? Should I send a transaction now or wait for lower fees? How much would I save by waiting?

Uses `get_fee_recommendation` + `analyze_mempool` + `compare_fee_estimates`. Returns plain-English advice with specific sat/vB rates and estimated savings.

### "Did I overpay on this transaction?"

> Analyze transaction `<txid>` and tell me if I overpaid on the fee. What's the current rate for the same priority? Show the difference in dollars.

Uses `analyze_transaction` + `compare_fee_estimates` + `get_btc_price`. Retroactive fee audit — shows exactly how much you could have saved.

### "Track this payment"

> Track this transaction and tell me when it's safe to consider confirmed: `<txid>`

Uses `analyze_transaction` + mempool tools. Reports confirmation count, fee rate paid, whether it's likely to confirm in the next block, and RBF status.

### "What fee should I set for a 2-input, 1-output Taproot transaction?"

> I'm building a transaction with 2 P2TR inputs and 1 P2TR output. What fee should I set for confirmation within 3 blocks?

The agent calculates exact vsize for your transaction shape, then checks current fee rates to give you a precise sat amount — not a guess.

### "Decode this transaction"

> Decode and explain this transaction: `<txid>`

Full breakdown: inputs, outputs, fee rate, SegWit/Taproot flags, inscription detection, script types. Plain English, not raw hex.

### "What's happening in the mempool right now?"

> Analyze the current mempool. How congested is it? What's the fee distribution? How many transactions are waiting?

Returns congestion level (low/medium/high), fee bucket breakdown, next-block minimum fee, and total pending transaction count.

### "How much Bitcoin exists right now?"

> What's the current Bitcoin supply? When is the next halving? What's the inflation rate compared to the Fed's target?

Uses `get_supply_info`. Returns circulating supply, percentage mined, halving countdown, and annual inflation rate — all derived from live node data.

### "Is my node healthy?"

> Run a full health check on my Bitcoin node. Check sync status, peer connections, and network health.

Comprehensive report: sync progress, peer count and quality, protocol version, disk usage, mempool state, difficulty adjustment progress.

### "When is the cheapest time to send?"

> Look at fee history for the last 24 hours. When were fees lowest? Is there a pattern?

Historical fee analysis showing the cheapest window, peak fees, and current position relative to the range.

### "What will the next block look like?"

> Analyze the current block template. What transactions are likely to be included? What's the minimum fee to get in?

Shows the projected next block: transaction count, total fees, fee percentiles, and the top-paying transactions waiting to confirm.

### "Compare urgency levels"

> Compare fee rates for different urgency levels. How much more does next-block confirmation cost vs. waiting an hour? Show me in dollars.

Side-by-side comparison: next block vs. ~1 hour vs. ~1 day. Shows exact cost in sats and USD for your specific transaction shape.

### "When is the next halving?"

> How many blocks until the next Bitcoin halving? What will the new block reward be?

Uses `get_halving_countdown`. Returns blocks remaining, estimated days, and the subsidy change — based on actual block production rate, not the assumed 10-minute average.

### "Monitor for whale transactions"

> Watch the mempool for any transaction moving more than 10 BTC.

Real-time whale alert: streams large transactions as they enter the mempool with value, fee rate, and size.

### "What's the current Bitcoin price?"

> What's the BTC/USD price right now? How has it changed in the last 24 hours?

Uses `get_btc_price`. Returns price, 24h change, and market cap from CoinGecko — no API key needed.

---

## 43 Tools

### Node & Network (3 tools)
| Tool | Description |
|------|-------------|
| `get_node_status` | Chain, height, sync progress, disk, connections, version |
| `get_peer_info` | Connected peer addresses, latency, services |
| `get_network_info` | Protocol version, relay fee, warnings |

### Blockchain & Blocks (6 tools)
| Tool | Description |
|------|-------------|
| `analyze_block` | Full analysis: pool ID, SegWit/Taproot adoption, fee distribution |
| `get_blockchain_info` | Chain, difficulty, softforks, chain work |
| `get_block_stats` | Raw statistics: median fee, total output, subsidy |
| `get_chain_tx_stats` | Transaction rate over N blocks |
| `get_chain_tips` | Active chain, forks, and stale branches |
| `search_blocks` | Block stats for a range of heights (max 10) |

### Mempool (4 tools)
| Tool | Description |
|------|-------------|
| `analyze_mempool` | Fee buckets, congestion level, next-block minimum fee |
| `get_mempool_entry` | Details of a specific unconfirmed tx |
| `get_mempool_info` | Quick stats: count, bytes, min relay fee |
| `get_mempool_ancestors` | Ancestor transactions for CPFP analysis |

### Transactions (4 tools)
| Tool | Description |
|------|-------------|
| `analyze_transaction` | Full decode + inscription detection + fee analysis |
| `decode_raw_transaction` | Decode raw hex without input lookup |
| `send_raw_transaction` | Broadcast a signed transaction (with fee safety limit) |
| `check_utxo` | Check if a specific output is unspent |

### Fee Estimation (5 tools)
| Tool | Description |
|------|-------------|
| `get_fee_estimates` | Rates for 1/3/6/25/144 block targets |
| `get_fee_recommendation` | Plain-English send/wait advice with raw rate data |
| `estimate_smart_fee` | Custom confirmation target |
| `compare_fee_estimates` | Side-by-side urgency labels + cost for 140vB tx |
| `estimate_transaction_cost` | **Cost in sats AND USD** by address type, inputs, outputs — with savings from waiting |

### Mining (3 tools)
| Tool | Description |
|------|-------------|
| `get_mining_info` | Difficulty, hashrate, block size |
| `analyze_next_block` | Block template: revenue, fee percentiles, top-fee txs |
| `get_mining_pool_rankings` | Top 10 mining pools by hashrate share and block count (via mempool.space) |

### UTXO Set (2 tools)
| Tool | Description |
|------|-------------|
| `get_utxo_set_info` | Total UTXOs, supply, disk size (slow: ~1-2 min) |
| `get_block_count` | Current block height (fast) |

### Price & Supply (4 tools)
| Tool | Description |
|------|-------------|
| `get_btc_price` | BTC/USD price, 24h change, market cap (CoinGecko, no API key) |
| `get_supply_info` | Circulating supply, inflation rate, halving countdown from live node |
| `get_halving_countdown` | Focused countdown: blocks remaining, estimated date, subsidy change |
| `get_market_sentiment` | Bitcoin Fear & Greed Index with 7-day history (via alternative.me) |

### Wallet (1 tool)
| Tool | Description |
|------|-------------|
| `generate_keypair` | Generate new Bitcoin address + private key via node wallet (legacy/segwit/taproot) |

### AI Developer Tools (10 tools)
| Tool | Description |
|------|-------------|
| `get_situation_summary` | **One-call briefing**: price + fees + mempool + chain tip + typical tx cost in USD |
| `describe_rpc_command` | Structured help for any RPC command |
| `list_rpc_commands` | All commands grouped by category |
| `search_blockchain` | Smart router: auto-detects txid, block hash/height, or address |
| `explain_script` | Decode script hex into readable opcodes |
| `get_address_utxos` | Scan UTXO set for an address |
| `validate_address` | Validate and classify address type (P2PKH/P2SH/P2WPKH/P2WSH/P2TR) |
| `get_difficulty_adjustment` | Epoch progress, estimated adjustment percentage |
| `compare_blocks` | Side-by-side block statistics comparison |

### Lightning (1 tool)
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
| Tools / Prompts / Resources | **43 / 6 / 7** | Fewer |
| Fee estimates in USD | **Yes** (live BTC price) | No |
| "Should I send now?" | **Yes** (saves you money) | No |
| Data source | Your local node | Third-party APIs |
| No-node fallback | Satoshi API remote | N/A |
| Mempool analysis | Fee bucketing, congestion, CPFP | Basic stats only |
| Inscription detection | Yes | No |
| Pool identification | Yes | No |
| SegWit/Taproot metrics | Yes | No |
| Next-block prediction | Yes | No |
| Supply & halving data | Yes | No |
| Agent workflow prompts | 6 built-in | None |
| Rate limits | None | API-dependent |

## CLI

```bash
bitcoin-mcp              # Start MCP server (default)
bitcoin-mcp --version    # Print version
bitcoin-mcp --check      # Test RPC connection and exit
```

## Requirements

- Python 3.10+
- Internet connection (uses hosted API by default) **or** local Bitcoin Core/Knots node

## Troubleshooting

**Tools not showing up in Claude Code?**
```bash
claude mcp add bitcoin -s user -- bitcoin-mcp
```
Then restart Claude Code. Verify with `claude mcp list`.

**"Cannot reach Satoshi API" errors?**
Check your internet connection. The hosted API at `https://bitcoinsapi.com` should be reachable. Run `bitcoin-mcp --check` to diagnose.

**Want to use a specific API instance?**
```bash
claude mcp add bitcoin -s user -e SATOSHI_API_URL=https://your-api.example.com -- bitcoin-mcp
```

## Related

- [Satoshi API](https://github.com/Bortlesboat/bitcoin-api) — REST API for Bitcoin nodes (pairs with bitcoin-mcp for remote access)
- [bitcoinlib-rpc](https://github.com/Bortlesboat/bitcoinlib-rpc) — the Python library powering this server
- [Bitcoin Protocol Guide](https://bortlesboat.github.io/bitcoin-protocol-guide/) — educational companion

## License

MIT
