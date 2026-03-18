"""
Transaction Investigation Example

Demonstrates using bitcoin-mcp tools to decode, analyze, and track
Bitcoin transactions — including inscription and ordinal detection.

Usage with Claude Code:
    claude mcp add bitcoin -- uvx bitcoin-mcp
    Then ask: "Analyze this transaction: <txid>"
"""

# MCP tool calls an AI agent would make:
#
# 1. analyze_transaction(txid="abc123...")
#    Returns: full transaction decode with:
#    - Input/output breakdown with addresses and amounts
#    - Fee paid and fee rate (sat/vB)
#    - Inscription detection (Ordinals, BRC-20, Runes)
#    - OP_RETURN data parsing
#    - Confirmation status and block height
#
# 2. check_utxo(txid="abc123...", vout=0)
#    Returns: whether a specific output is spent or unspent
#    Essential for wallet verification and UTXO management
#
# 3. decode_raw_transaction(hex="0200000001...")
#    Returns: human-readable decode of a raw transaction hex
#    Useful for verifying transactions before broadcasting
#
# 4. explain_script(hex="76a914...")
#    Returns: plain-English explanation of a Bitcoin script
#    Demystifies P2PKH, P2SH, P2WPKH, P2TR, and custom scripts
#
# Example conversation:
#
#   User: "What happened in tx abc123...?"
#   Agent: [calls analyze_transaction]
#   Agent: "This transaction sent 0.15 BTC from bc1q...xyz to
#           bc1p...abc (Taproot address). It paid 1,240 sats in fees
#           (6.2 sat/vB), confirmed in block 892,411. No inscriptions
#           detected. The change output (0.0032 BTC) went back to
#           the sender's address."
