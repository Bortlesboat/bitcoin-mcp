# bitcoin-mcp — MCP Server for Bitcoin

## What this is
47-tool MCP server wrapping Bitcoin Core/Knots RPC. Zero-config: auto-falls back to Satoshi API (bitcoinsapi.com) when no local node detected. Published to PyPI and Smithery. v0.5.0.

## Key files
- `src/bitcoin_mcp/server.py` — all 49 tools defined as `@mcp.tool()` decorators
- `src/bitcoin_mcp/l402_client.py` — L402 payment channel client
- `tests/` — 116 tests, must pass before any release

## Tool categories (all in server.py)
- **Mempool**: analyze_mempool, get_mempool_info, get_mempool_entry, get_mempool_ancestors
- **Fees**: get_fee_estimates, estimate_smart_fee, get_fee_recommendation, estimate_transaction_cost, compare_fee_estimates
- **Blocks**: analyze_block, get_block_stats, compare_blocks, search_blocks, get_block_count
- **Transactions**: analyze_transaction, decode_raw_transaction, get_indexed_transaction, search_blockchain, decode_bolt11_invoice
- **Address**: get_address_balance, get_address_history, get_address_utxos, check_utxo, validate_address, get_indexer_status
- **Mining**: get_mining_info, get_difficulty_adjustment, get_halving_countdown, get_mining_pool_rankings
- **Network**: get_network_info, get_blockchain_info, get_chain_tips, get_peer_info, get_node_status
- **Supply**: get_supply_info, get_utxo_set_info, get_chain_tx_stats
- **Security**: analyze_psbt_security, explain_inscription_listing_security
- **Utility**: generate_keypair, explain_script, describe_rpc_command, list_rpc_commands, query_remote_api
- **Market**: get_btc_price, get_market_sentiment, get_situation_summary, get_next_block_eta

## Development rules
- Bump version in `pyproject.toml` for any release (semver)
- Run `pytest tests/` before any commit — all 116 must pass
- Tools must work against BOTH local Bitcoin Core AND the Satoshi API fallback
- No breaking changes to tool signatures without a major version bump
- Tool docstrings appear in MCP client UIs — keep them accurate and useful
- Discoverability matters: Glama/Smithery rank by stars + docs. Keep README and per-tool examples current.

## Current focus
- Improve Glama ranking: add per-tool usage examples, increase release cadence
- Submit to remaining registries: smithery (done), pulsemcp (web form), mcpservers.org (web form)
