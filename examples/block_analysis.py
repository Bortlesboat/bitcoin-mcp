"""
Block Analysis Example

Demonstrates using bitcoin-mcp tools to inspect, compare, and
analyze Bitcoin blocks — useful for mining analysis, chain monitoring,
and historical research.

Usage with Claude Code:
    claude mcp add bitcoin -- uvx bitcoin-mcp
    Then ask: "Analyze the latest Bitcoin block"
"""

# MCP tool calls an AI agent would make:
#
# 1. analyze_block(height=892411)
#    Returns: deep block analysis including:
#    - Block header (hash, timestamp, nonce, difficulty)
#    - Transaction count and total value transferred
#    - Fee statistics (total fees, min/max/median fee rate)
#    - Miner identification (pool name if known)
#    - SegWit/Taproot adoption percentage
#
# 2. get_block_stats(height=892411)
#    Returns: statistical breakdown with percentiles
#    Useful for research and fee market analysis
#
# 3. compare_blocks(height_a=892410, height_b=892411)
#    Returns: side-by-side comparison of two blocks
#    Great for spotting anomalies or mining pattern changes
#
# 4. search_blocks(start_height=892400, end_height=892411)
#    Returns: summary of a block range
#    Useful for time-period analysis
#
# Example conversation:
#
#   User: "Tell me about the latest block"
#   Agent: [calls get_block_count, then analyze_block]
#   Agent: "Block 892,411 was mined by Foundry USA 12 minutes ago.
#           It contains 3,241 transactions moving 1,847 BTC total.
#           Median fee rate was 4.2 sat/vB. 78% of transactions
#           used SegWit, 23% used Taproot. The block was 99.7% full
#           (3.98 MB weight)."
