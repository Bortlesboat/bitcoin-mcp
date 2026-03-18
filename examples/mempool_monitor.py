"""
Mempool Monitoring Example

Demonstrates using bitcoin-mcp tools to monitor mempool congestion
and understand pending transaction flow.

Usage with Claude Code:
    claude mcp add bitcoin -- uvx bitcoin-mcp
    Then ask: "Monitor the mempool and tell me about congestion"
"""

# MCP tool calls an AI agent would make:
#
# 1. analyze_mempool()
#    Returns: full mempool analysis — depth, fee tiers, congestion score
#    {
#      "size": 45000,
#      "bytes": 28000000,
#      "fee_histogram": [...],
#      "congestion": "moderate"
#    }
#
# 2. get_mempool_info()
#    Returns: raw mempool stats — size, bytes, min fee floor
#
# 3. get_mempool_entry(txid="abc123...")
#    Returns: details for a specific unconfirmed transaction
#    Useful for tracking your own pending transaction
#
# 4. get_mempool_ancestors(txid="abc123...")
#    Returns: ancestor chain showing CPFP fee-bumping opportunities
#
# Example conversation:
#
#   User: "Is the mempool congested right now?"
#   Agent: [calls analyze_mempool]
#   Agent: "The mempool has 45,000 pending transactions (28 MB).
#           Congestion is moderate. The minimum fee to get into the
#           next block is 3 sat/vB, but 1 sat/vB transactions should
#           confirm within 6 blocks (~1 hour). If you're not in a
#           rush, wait — fees typically drop overnight."
