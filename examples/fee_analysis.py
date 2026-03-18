"""
Fee Analysis Example

Demonstrates using bitcoin-mcp tools to analyze current fee conditions
and find the optimal time to send a Bitcoin transaction.

Usage with Claude Code:
    claude mcp add bitcoin -- uvx bitcoin-mcp
    Then ask: "Analyze current fee conditions using the bitcoin tools"

Usage programmatically:
    This shows the tool calls an AI agent would make.
"""

# These are the MCP tool calls an AI agent makes behind the scenes:
#
# 1. get_fee_recommendation()
#    Returns: optimal fee rate, urgency tiers, savings tips
#    Example response:
#    {
#      "recommendation": "Fees are low. Good time to send.",
#      "estimates": {"high": 4, "medium": 2, "low": 1},
#      "mempool_pressure": "low"
#    }
#
# 2. compare_fee_estimates()
#    Returns: side-by-side comparison of fee sources
#    Shows difference between node estimates and mempool-derived rates
#
# 3. estimate_transaction_cost(inputs=2, outputs=2, fee_rate=4)
#    Returns: exact cost in sats and USD for your transaction
#    Accounts for input/output count, SegWit discount, and current rates
#
# Example conversation:
#
#   User: "I want to send 0.5 BTC. What should I pay?"
#   Agent: [calls get_fee_recommendation]
#   Agent: "Fees are currently low at 2 sat/vB. For a typical 2-in/2-out
#           transaction, that's about 282 sats ($0.28). If you wait for
#           next block, you'd pay 4 sat/vB (564 sats). Sending now saves
#           you 50%."
