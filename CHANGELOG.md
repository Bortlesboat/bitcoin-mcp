# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-14

### Added
- PSBT security analysis tools (analyze and explain PSBT risks before signing)
- Indexed address balance lookup via indexer (Electrum/mempool.space)
- Indexed address transaction history
- Indexed transaction lookup by txid
- Indexer status reporting
- mempool.space fallback for indexed address tools when no local indexer is available
- CLI flags: `--transport`, `--host`, `--port` for flexible server configuration

### Changed
- Tool count increased to 49 (47 core + 2 PSBT tools)
- README overhauled with Context7-style landing page, comparison table, and SEO keywords

## [0.4.2] - 2026-03-09

### Added
- Zero-config mode: automatically falls back to Satoshi API when no local Bitcoin node is detected
- No configuration required to start using the server

### Changed
- Updated test count to 108

## [0.4.1] - 2026-03-09

### Added
- Docker support via Dockerfile
- Security hardening improvements

### Changed
- Tool count increased to 43
- Test count increased to 103

## [0.4.0] - 2026-03-08

### Added
- `get_btc_price` tool for real-time BTC/USD pricing
- `get_supply_info` tool for circulating/max supply data
- `get_halving_countdown` tool for next halving estimates
- USD pricing integrated into fee estimation tools
- `get_situation_summary` tool upgrade with richer context
- 16 prompt recipes for common Bitcoin analysis workflows

### Changed
- Tool count increased to 40

## [0.3.0] - 2026-03-07

### Added
- `send_raw_transaction` tool for broadcasting signed transactions
- `decode_bolt11_invoice` tool for Lightning Network BOLT11 invoice decoding
- Connection status resource for monitoring node connectivity
- Multi-network support (mainnet, testnet, signet, regtest)
- CLI interface for running the server

## [0.2.1] - 2026-03-07

### Added
- MCP Registry metadata for official listing

## [0.2.0] - 2026-03-06

### Added
- Expanded tool set to 32 tools
- 6 prompt templates for guided Bitcoin analysis
- 6 resources for structured data access

## [0.1.0] - 2026-03-04

### Added
- Initial release of bitcoin-mcp
- 20 core tools for Bitcoin node interaction via MCP
- Block analysis, mempool inspection, fee estimation
- Transaction decoding and script explanation
- Network and mining info queries
- Peer information and chain tip data
- Address validation and key pair generation

[0.5.0]: https://github.com/Bortlesboat/bitcoin-mcp/compare/v0.4.2...HEAD
[0.4.2]: https://github.com/Bortlesboat/bitcoin-mcp/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/Bortlesboat/bitcoin-mcp/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Bortlesboat/bitcoin-mcp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Bortlesboat/bitcoin-mcp/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Bortlesboat/bitcoin-mcp/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Bortlesboat/bitcoin-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Bortlesboat/bitcoin-mcp/releases/tag/v0.1.0
