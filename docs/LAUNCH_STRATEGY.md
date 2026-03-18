# Launch Strategy — bitcoin-mcp

*Created: 2026-03-17*

---

## Current State
- **v0.5.1** on PyPI, ~256 downloads/month (organic, zero promotion)
- 49 tools, 6 prompts, 7 resources, 116 tests
- Smithery: LIVE. 5 awesome-list PRs: OPEN. MCP Registry: PENDING (device auth)
- mcpservers.org and PulseMCP: forms prepared, not submitted
- Zero marketing spend, zero content

## Strategic Role
bitcoin-mcp is NOT a standalone product. It's the **AI distribution layer** for Satoshi API. Every bitcoin-mcp install without a local node = automatic Satoshi API user.

**Funnel:** pip install bitcoin-mcp → use in Claude → hits Satoshi API → registers for key → upgrades to Pro

---

## ORB Channels

### Owned
- PyPI package page (primary discovery)
- GitHub README (second discovery)
- bitcoinsapi.com/mcp-setup (setup guide)
- bitcoinsapi.com/bitcoin-mcp-setup-guide (SEO page)

### Rented
- MCP directories (Smithery, mcpservers.org, PulseMCP, Glama, mcp.so)
- awesome-lists on GitHub (5 PRs open)
- Reddit (r/LocalLLaMA, r/ClaudeAI, r/Bitcoin)
- Twitter (@BTCOrangeCoin)

### Borrowed
- Other MCP server authors (cross-promotion)
- Claude Desktop extension ecosystem (when .dxt launches)
- AI developer newsletters/blogs

---

## Launch Plan

### Phase 1: Directory Saturation (This Week)

**Submit to every MCP directory that exists:**

| Directory | Status | Action |
|-----------|--------|--------|
| Smithery | LIVE | Done |
| mcpservers.org | Form ready | Submit now |
| PulseMCP | Form ready | Submit now |
| Glama | Pending | Follow up |
| mcp.so (chatmcp) | Comment posted | Follow up on issue #1 |
| MCP Registry (official) | Pending device auth | Complete when available |
| punkpeye/awesome-mcp-servers | PR #2847 open | Ping maintainer |
| appcypher/awesome-mcp-servers | PR #543 open | Ping maintainer |
| royyannick/awesome-blockchain-mcps | PR #25 open | Ping maintainer |
| badkk/awesome-crypto-mcp-servers | PR #25 open | Ping maintainer |
| webfuse-com/awesome-claude | PR #89 open | Ping maintainer |

**Goal:** Listed on 10+ directories within 2 weeks.

### Phase 2: README Optimization (This Week)

Current README has 16 recipes. Optimize for conversion:

1. **Hero section:** "Bitcoin data for AI agents. 49 tools. Zero config." + `pip install bitcoin-mcp`
2. **Quick demo:** Show a Claude conversation asking about fees → real answer
3. **One-command setup:** Make it dead simple
4. **Stats badge row:** PyPI downloads, version, tests passing, license
5. **"Why bitcoin-mcp?"** section: 3 bullet points (fee intelligence, zero config, 49 tools)
6. **Comparison table:** bitcoin-mcp (49 tools) vs nearest competitor (~7 tools)

### Phase 3: Content (Weeks 2-3)

| Content | Channel | Goal |
|---------|---------|------|
| "Bitcoin Data for Claude in 60 Seconds" | Dev.to | Tutorial, drives installs |
| "I gave Claude access to Bitcoin" | Twitter thread | Viral, screenshots |
| "MCP Servers for Bitcoin: A Comparison" | Blog | SEO, positions as leader |
| "How to Build a Bitcoin Bot with Claude" | Dev.to | Use case, drives installs |

### Phase 4: Community (Ongoing)

- Answer Bitcoin + AI questions on Reddit with bitcoin-mcp examples
- Engage in MCP Discord/community
- Cross-promote with other MCP server authors
- Post in Claude community forums

---

## Launch Assets

### Show HN (coordinate with Satoshi API launch)
```
Show HN: bitcoin-mcp – 49 Bitcoin tools for Claude and AI agents

I built an MCP server that gives AI agents access to real-time Bitcoin
data. Ask Claude "should I send Bitcoin now?" and it answers with live
fee data, mempool state, and a send-or-wait recommendation.

49 tools: fees, blocks, transactions, mempool, mining, supply, price,
UTXO, BOLT11 decoding, and more.

pip install bitcoin-mcp

Zero config — works immediately with our free hosted API. Or point it
at your own Bitcoin Core node for full sovereignty.

GitHub: https://github.com/Bortlesboat/bitcoin-mcp
PyPI: https://pypi.org/project/bitcoin-mcp/
```

### Reddit: r/LocalLLaMA
```
Title: I built an MCP server that gives Claude real-time Bitcoin data (49 tools)

bitcoin-mcp gives AI agents access to live Bitcoin data — fees, blocks,
mempool, mining, price, and more. 49 tools total.

Zero config: `pip install bitcoin-mcp`. Works with Claude Desktop out
of the box using the free hosted API. Or point it at your own node.

The coolest thing: ask Claude "should I send Bitcoin right now?" and it
uses real mempool data to answer.

Open source (MIT): github.com/Bortlesboat/bitcoin-mcp
```

### Reddit: r/ClaudeAI
```
Title: MCP server for Bitcoin data — fees, blocks, mempool, 49 tools

Made an MCP server that gives Claude access to live Bitcoin data.

pip install bitcoin-mcp

Then ask Claude about fees, blocks, transactions, mining, price —
anything Bitcoin. It uses real data from a Bitcoin Core node (or our
free hosted API if you don't have one).

49 tools, 116 tests, zero config.

What other data sources would be useful as MCP servers?
```

### Twitter Thread
```
I gave Claude access to live Bitcoin data. Here's what happened:

1/ "Should I send Bitcoin right now?"
Claude: "Fees are 28 sat/vB (high congestion). Wait 2 hours — projected
savings of 46%. Economy rate is 12 sat/vB."

This is possible because of bitcoin-mcp — 49 tools for Bitcoin data.

2/ pip install bitcoin-mcp

Zero config. It automatically connects to our free hosted API. Or point
it at your own Bitcoin Core node.

3/ What can it do?
- Fee intelligence (send-or-wait verdicts)
- Block data (latest, by height/hash)
- Transaction decoding (including inscriptions)
- Mempool analysis
- Mining pool rankings
- BTC price, supply, halving countdown
- BOLT11 invoice decoding
- And 40+ more

4/ The killer feature: zero-config fallback.

No Bitcoin node? No problem. bitcoin-mcp falls back to Satoshi API
(free hosted API) automatically. Every tool works out of the box.

5/ Open source (MIT), 116 tests, works with any MCP-compatible LLM.

pip install bitcoin-mcp
GitHub: github.com/Bortlesboat/bitcoin-mcp
```

---

## Metrics

| Metric | Now | Month 1 | Month 3 |
|--------|-----|---------|---------|
| PyPI downloads/month | 256 | 500 | 1,000 |
| GitHub stars | ~5 | 25 | 100 |
| Directory listings | 1 (Smithery) | 8 | 10+ |
| Satoshi API conversions from MCP | unknown | 50 | 200 |
| Content pieces published | 0 | 4 | 10 |

---

## Immediate Actions (This Session or Next)

1. [ ] Submit to mcpservers.org (form ready)
2. [ ] Submit to PulseMCP (form ready)
3. [ ] Follow up on 5 open awesome-list PRs
4. [ ] Follow up on Glama submission
5. [ ] Follow up on mcp.so issue #1
6. [ ] Post Twitter thread
7. [ ] Post r/LocalLLaMA
8. [ ] Post r/ClaudeAI
