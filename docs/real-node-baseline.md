# Real-node integration tests

These tests run five existing tools through an MCP client over stdio against a
real Bitcoin Core or Knots process. They complement the mocked unit tests.

The fixture starts an isolated regtest node, creates three blocks, and disables
wallets and peer networking. RPC is bound to loopback. Every run uses its own data
directory, empty configuration and cookie, then shuts down its child process.
It does not use an existing node or modify its configuration.

## Checks

| Tool | Expected result |
| --- | --- |
| `get_network_info` | Node version/subversion, zero peer connections and a valid relay fee |
| `get_blockchain_info` | Regtest chain at height 3, with matching headers and no pruning |
| `get_block_stats` | Height 3 and its generated block hash, one coinbase transaction, zero fees and the expected subsidy |
| `get_mempool_info` | Empty mempool and valid size/fee fields |
| `estimate_smart_fee` | Zero fee rate and an explicit insufficient-history error on the fresh chain |

No RPC responses or MCP tool results are mocked. The fee check preserves the
node's unavailable-estimate behavior; a zero rate is not a recommendation to
broadcast a transaction.

## Run locally

Download a portable node binary from [Bitcoin Core](https://bitcoincore.org/bin/bitcoin-core-30.2/)
or [Bitcoin Knots](https://bitcoinknots.org/). Verify its release checksum and
signatures before running it. An installed binary can also be used: the fixture
supplies its own configuration and data directory.

From this repository, on PowerShell:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -e '.[dev]'
$env:BITCOIN_MCP_TEST_BITCOIND = 'C:/path/to/verified/bitcoind.exe'
.venv/Scripts/python.exe -m pytest tests/integration/test_real_node.py -v
```

On Linux:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
export BITCOIN_MCP_TEST_BITCOIND=/path/to/verified/bitcoind
.venv/bin/python -m pytest tests/integration/test_real_node.py -v
```

Without `BITCOIN_MCP_TEST_BITCOIND`, the five integration tests skip and the
ordinary unit suite still runs. Supplying a missing or unusable binary produces
an error instead of a passing integration result.

If a shared pytest temp directory is inaccessible, select a new, disposable
directory with `--basetemp`. Pytest removes an existing directory at that path,
so use a fresh directory reserved for this run.

## Verified baseline

On October 9, 2026, the five MCP checks passed locally on Windows with Python
3.12.9 against each of:

- Bitcoin Core 30.2, using `bitcoin-30.2-win64.zip`.
- Bitcoin Knots 29.4.2.knots20260508, using its portable PGP-verifiable ZIP.

The pre-change unit suite passed all 180 tests. The integration baseline covers
these five tools on a fresh regtest chain. It does not establish compatibility
for every tool, node version, mainnet workload or remote API backend.

The [real-node workflow](../.github/workflows/real-node.yml) provisions pinned
Linux releases with fixed SHA-256 hashes and uploads JUnit results. It runs for
relevant pull requests and main-branch changes and can also be started manually.
Remote CI results are separate evidence from the local baseline above.
