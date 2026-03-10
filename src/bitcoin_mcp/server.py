"""Bitcoin MCP Server — 47 tools for AI agents to query Bitcoin."""

import argparse
import json
import logging
import os
import re
import sys
import urllib.request
import urllib.error

from mcp.server.fastmcp import FastMCP

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.blocks import analyze_block as _analyze_block
from bitcoinlib_rpc.fees import get_fee_estimates as _get_fee_estimates
from bitcoinlib_rpc.mempool import analyze_mempool as _analyze_mempool
from bitcoinlib_rpc.nextblock import analyze_next_block as _analyze_next_block
from bitcoinlib_rpc.status import get_status as _get_status
from bitcoinlib_rpc.transactions import analyze_transaction as _analyze_transaction
from bitcoinlib_rpc.utils import fee_recommendation

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("bitcoin-mcp")

mcp = FastMCP(
    "bitcoin",
    instructions=(
        "Query and analyze the Bitcoin network. "
        "Works automatically with a local Bitcoin Core/Knots node or the free hosted Satoshi API — no configuration needed. "
        "Provides mempool analysis, fee estimation, block inspection, "
        "transaction decoding with inscription detection, and mining insights."
    ),
)

# --- RPC connection (lazy singleton) ---

_rpc = None  # BitcoinRPC or _SatoshiRPC

_DEFAULT_API_URL = "https://bitcoinsapi.com"

NETWORK_PORTS = {
    "mainnet": 8332,
    "testnet": 18332,
    "signet": 38332,
    "regtest": 18443,
}


def _default_port() -> int:
    """Return the default RPC port based on BITCOIN_NETWORK env var."""
    network = os.getenv("BITCOIN_NETWORK", "mainnet").lower()
    return NETWORK_PORTS.get(network, 8332)


class _SatoshiRPC:
    """Lightweight JSON-RPC client that proxies calls through the Satoshi API.

    Drop-in replacement for BitcoinRPC when no local node is available.
    Routes all RPC calls through the /api/v1/rpc proxy endpoint.
    """

    def __init__(self, api_url: str):
        self._url = f"{api_url.rstrip('/')}/api/v1/rpc"
        self._id = 0

    def __getattr__(self, name: str):
        def method(*args, **kwargs):
            return self._call(name, *args)
        return method

    def _call(self, method: str, *args):
        self._id += 1
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": self._id,
            "method": method,
            "params": list(args),
        }).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "bitcoin-mcp"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read(10_000_000))
        except urllib.error.HTTPError as e:
            body = e.read(10_000_000).decode(errors="replace")
            try:
                err = json.loads(body)
                msg = err.get("error", {}).get("message", body)
            except Exception:
                msg = body
            raise ConnectionError(f"Satoshi API RPC error: {msg}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot reach Satoshi API at {self._url}: {e.reason}"
            ) from e

        if "error" in data and data["error"]:
            err = data["error"]
            raise ConnectionError(f"RPC error {err.get('code', '?')}: {err.get('message', err)}")

        return data.get("result")


def get_rpc():
    """Return an RPC connection — local node preferred, Satoshi API fallback.

    Connection priority:
    1. Local Bitcoin Core node (if RPC credentials or cookie file found)
    2. Satoshi API RPC proxy (SATOSHI_API_URL env var, or default https://bitcoinsapi.com)

    This means bitcoin-mcp works with ZERO configuration for most users.
    """
    global _rpc
    if _rpc is not None:
        return _rpc

    # 1. Try local node first
    has_explicit_rpc = (
        os.getenv("BITCOIN_RPC_USER")
        or os.getenv("BITCOIN_RPC_PASSWORD")
        or os.getenv("BITCOIN_DATADIR")
        or os.getenv("BITCOIN_RPC_HOST")
        or os.getenv("BITCOIN_RPC_PORT")
    )
    try:
        port_str = os.getenv("BITCOIN_RPC_PORT")
        port = int(port_str) if port_str else _default_port()
        _rpc = BitcoinRPC(
            host=os.getenv("BITCOIN_RPC_HOST", "127.0.0.1"),
            port=port,
            user=os.getenv("BITCOIN_RPC_USER"),
            password=os.getenv("BITCOIN_RPC_PASSWORD"),
            datadir=os.getenv("BITCOIN_DATADIR"),
        )
        logger.info("Connected to local Bitcoin node")
        return _rpc
    except ConnectionError:
        if has_explicit_rpc:
            # User explicitly configured local node but it failed — don't silently fall back
            raise
        # No local node found — fall through to Satoshi API

    # 2. Fall back to Satoshi API RPC proxy
    api_url = os.getenv("SATOSHI_API_URL", _DEFAULT_API_URL)
    logger.info("No local node found — using Satoshi API (%s)", api_url)
    _rpc = _SatoshiRPC(api_url)
    return _rpc


# ============================================================
# NODE & NETWORK (3 tools)
# ============================================================


@mcp.tool()
def get_node_status() -> str:
    """Get Bitcoin network status: chain, height, sync progress, disk usage, connections, version. In hosted API mode, reflects the API server's node."""
    status = _get_status(get_rpc())
    return status.model_dump_json()


@mcp.tool()
def get_peer_info() -> str:
    """Get connected peer details: addresses, latency, services, version. In hosted API mode, shows the API server's peers."""
    peers = get_rpc().getpeerinfo()
    summary = []
    for p in peers[:20]:  # limit to 20
        summary.append({
            "addr": p.get("addr"),
            "subver": p.get("subver"),
            "pingtime": p.get("pingtime"),
            "synced_blocks": p.get("synced_blocks"),
            "connection_type": p.get("connection_type"),
        })
    return json.dumps(summary)


@mcp.tool()
def get_network_info() -> str:
    """Get network info: protocol version, relay fee, connections, warnings. In hosted API mode, reflects the API server's network view."""
    info = get_rpc().getnetworkinfo()
    return json.dumps({
        "version": info["version"],
        "subversion": info["subversion"],
        "protocolversion": info["protocolversion"],
        "connections": info["connections"],
        "connections_in": info.get("connections_in", 0),
        "connections_out": info.get("connections_out", 0),
        "relayfee": info["relayfee"],
        "warnings": info.get("warnings", ""),
    })


# ============================================================
# BLOCKCHAIN & BLOCKS (6 tools)
# ============================================================


@mcp.tool()
def get_blockchain_info() -> str:
    """Get blockchain info: chain, difficulty, softfork statuses, chain work, pruning."""
    info = get_rpc().getblockchaininfo()
    return json.dumps({
        "chain": info["chain"],
        "blocks": info["blocks"],
        "headers": info["headers"],
        "difficulty": info["difficulty"],
        "verificationprogress": info["verificationprogress"],
        "size_on_disk": info["size_on_disk"],
        "pruned": info["pruned"],
        "softforks": info.get("softforks", {}),
    })


@mcp.tool()
def analyze_block(height_or_hash: str) -> str:
    """Analyze a block: mining pool, SegWit/Taproot adoption, fee distribution, revenue.

    Args:
        height_or_hash: Block height (e.g. "939290") or block hash
    """
    analysis = _analyze_block(get_rpc(), height_or_hash)
    return analysis.model_dump_json()


@mcp.tool()
def get_block_stats(height: int) -> str:
    """Get raw block statistics: median fee, total output, subsidy, weight, tx count.

    Args:
        height: Block height
    """
    stats = get_rpc().getblockstats(height)
    return json.dumps(stats)


@mcp.tool()
def get_chain_tx_stats(nblocks: int = 2016) -> str:
    """Get transaction rate statistics over N blocks.

    Args:
        nblocks: Number of blocks to average over (default 2016 = ~2 weeks)
    """
    stats = get_rpc().getchaintxstats(nblocks)
    return json.dumps(stats)


@mcp.tool()
def get_chain_tips() -> str:
    """Get chain tips: active chain, forks, and stale branches. Useful for detecting chain splits."""
    tips = get_rpc().getchaintips()
    return json.dumps(tips)


@mcp.tool()
def search_blocks(start_height: int, end_height: int) -> str:
    """Get block statistics for a range of heights. Max 10 blocks.

    Args:
        start_height: Starting block height (inclusive)
        end_height: Ending block height (inclusive)
    """
    if end_height - start_height + 1 > 10:
        return json.dumps({"error": "Maximum range is 10 blocks. Narrow your search."})
    if start_height > end_height:
        return json.dumps({"error": "start_height must be <= end_height"})
    results = []
    for h in range(start_height, end_height + 1):
        stats = get_rpc().getblockstats(h)
        results.append({
            "height": h,
            "time": stats.get("time"),
            "txs": stats.get("txs"),
            "total_fee": stats.get("totalfee"),
            "avg_fee_rate": stats.get("avgfeerate"),
            "median_fee_rate": stats.get("feerate_percentiles", [None, None, None])[2] if "feerate_percentiles" in stats else stats.get("medianfee"),
            "total_weight": stats.get("total_weight"),
            "total_size": stats.get("total_size"),
        })
    return json.dumps(results)


# ============================================================
# MEMPOOL (4 tools)
# ============================================================


@mcp.tool()
def analyze_mempool() -> str:
    """Analyze the mempool: tx count, fee buckets, congestion level, next-block minimum fee."""
    summary = _analyze_mempool(get_rpc())
    return summary.model_dump_json()


@mcp.tool()
def get_mempool_entry(txid: str) -> str:
    """Get details of a specific unconfirmed transaction in the mempool.

    Args:
        txid: Transaction hash (64 hex characters)
    """
    entry = get_rpc().getmempoolentry(txid)
    return json.dumps(entry)


@mcp.tool()
def get_mempool_info() -> str:
    """Get quick mempool stats: transaction count, size in bytes, min relay fee."""
    info = get_rpc().getmempoolinfo()
    return json.dumps({
        "size": info["size"],
        "bytes": info["bytes"],
        "usage": info["usage"],
        "maxmempool": info["maxmempool"],
        "mempoolminfee": info["mempoolminfee"],
        "minrelaytxfee": info["minrelaytxfee"],
    })


@mcp.tool()
def get_mempool_ancestors(txid: str) -> str:
    """Get all unconfirmed ancestor transactions of a mempool transaction. Useful for CPFP analysis.

    Args:
        txid: Transaction hash (64 hex characters)
    """
    try:
        ancestors = get_rpc().getmempoolancestors(txid, True)
    except Exception as e:
        return json.dumps({"error": str(e)})
    summary = []
    for anc_txid, info in ancestors.items():
        summary.append({
            "txid": anc_txid,
            "fee_sats": info.get("fees", {}).get("base", 0) * 1e8,
            "vsize": info.get("vsize"),
            "fee_rate_sat_vb": round(info.get("fees", {}).get("base", 0) * 1e8 / info.get("vsize", 1), 2) if info.get("vsize") else None,
            "depends": info.get("depends", []),
        })
    return json.dumps({
        "txid": txid,
        "ancestor_count": len(ancestors),
        "ancestors": summary,
    })


# ============================================================
# TRANSACTIONS (4 tools)
# ============================================================


@mcp.tool()
def analyze_transaction(txid: str) -> str:
    """Decode and analyze a transaction: inputs, outputs, fee rate, SegWit/Taproot flags, inscription detection.

    Args:
        txid: Transaction hash (64 hex characters). Local nodes need txindex=1 for confirmed txs; the hosted API handles this automatically.
    """
    analysis = _analyze_transaction(get_rpc(), txid)
    return analysis.model_dump_json()


@mcp.tool()
def decode_raw_transaction(hex_string: str) -> str:
    """Decode a raw transaction hex without looking up inputs.

    Args:
        hex_string: Raw transaction in hex format
    """
    if not re.fullmatch(r"[a-fA-F0-9]+", hex_string):
        return json.dumps({"error": "Invalid hex string: must contain only hex characters [0-9a-fA-F]"})
    if len(hex_string) > 2_000_000:
        return json.dumps({"error": "Hex string too long: maximum 2,000,000 characters (1MB transaction)"})
    result = get_rpc().decoderawtransaction(hex_string)
    return json.dumps(result)


@mcp.tool()
def check_utxo(txid: str, vout: int) -> str:
    """Check if a specific transaction output is unspent (UTXO lookup).

    Args:
        txid: Transaction hash
        vout: Output index
    """
    result = get_rpc().gettxout(txid, vout)
    if result is None:
        return json.dumps({"spent": True, "message": "Output is spent or does not exist"})
    return json.dumps({"spent": False, "utxo": result})


@mcp.tool()
def send_raw_transaction(hex_string: str, max_fee_rate: float = 0.10) -> str:
    """Broadcast a signed raw transaction to the Bitcoin network.

    WARNING: This sends a REAL transaction. Once broadcast, it cannot be reversed.
    Ensure the transaction is correctly signed and you understand the fee implications.
    In hosted API mode, the transaction is broadcast through the Satoshi API's node.

    Args:
        hex_string: Signed raw transaction in hex format
        max_fee_rate: Maximum fee rate in BTC/kvB to prevent accidental overpayment (default 0.10)
    """
    if not re.fullmatch(r"[a-fA-F0-9]+", hex_string):
        return json.dumps({"error": "Invalid hex string: must contain only hex characters [0-9a-fA-F]", "broadcast": False})
    if len(hex_string) > 2_000_000:
        return json.dumps({"error": "Hex string too long: maximum 2,000,000 characters (1MB transaction)", "broadcast": False})
    try:
        txid = get_rpc().sendrawtransaction(hex_string, max_fee_rate)
        return json.dumps({"txid": txid, "broadcast": True})
    except Exception as e:
        return json.dumps({"error": str(e), "broadcast": False})


# ============================================================
# FEE ESTIMATION (5 tools)
# ============================================================


@mcp.tool()
def get_fee_estimates() -> str:
    """Get fee rate estimates for 1/3/6/25/144 block confirmation targets in sat/vB."""
    estimates = _get_fee_estimates(get_rpc())
    return json.dumps([e.model_dump() for e in estimates])


@mcp.tool()
def get_fee_recommendation() -> str:
    """Get a plain-English fee recommendation based on current estimates, with raw rate data."""
    estimates = _get_fee_estimates(get_rpc())
    rates = {e.conf_target: e.fee_rate_sat_vb for e in estimates if not e.errors}
    result = {
        "recommendation": fee_recommendation(rates),
        "rates": rates,
    }
    return json.dumps(result)


@mcp.tool()
def estimate_smart_fee(conf_target: int) -> str:
    """Get fee estimate for a specific confirmation target.

    Args:
        conf_target: Number of blocks for confirmation (1-1008)
    """
    result = get_rpc().estimatesmartfee(conf_target)
    fee_rate = result.get("feerate", 0)
    return json.dumps({
        "conf_target": conf_target,
        "fee_rate_btc_kvb": fee_rate,
        "fee_rate_sat_vb": fee_rate * 100_000,
        "errors": result.get("errors", []),
    })


@mcp.tool()
def compare_fee_estimates() -> str:
    """Compare fee estimates side-by-side with urgency labels and cost for a typical 140 vB transaction."""
    estimates = _get_fee_estimates(get_rpc())
    urgency_labels = {1: "Next Block", 3: "~30 min", 6: "~1 hour", 25: "~4 hours", 144: "~1 day"}
    rows = []
    for e in estimates:
        rate = e.fee_rate_sat_vb if not e.errors else None
        rows.append({
            "conf_target": e.conf_target,
            "urgency": urgency_labels.get(e.conf_target, f"~{e.conf_target} blocks"),
            "fee_rate_sat_vb": rate,
            "cost_140vb_sats": round(rate * 140) if rate else None,
            "cost_140vb_btc": round(rate * 140 / 1e8, 8) if rate else None,
            "errors": e.errors or None,
        })
    return json.dumps(rows)


@mcp.tool()
def estimate_transaction_cost(
    input_count: int = 1,
    output_count: int = 2,
    address_type: str = "p2wpkh",
) -> str:
    """Estimate Bitcoin transaction cost in sats AND USD at different urgency levels. Supports address types: p2pkh (legacy), p2sh-p2wpkh (nested segwit), p2wpkh (native segwit), p2tr (taproot). Shows how much you save by waiting."""
    try:
        rpc = get_rpc()

        # Estimate vbytes based on address type
        overhead = 10.5  # version + locktime + segwit marker
        witness_discount = 0.25

        type_sizes = {
            "p2pkh": {"input": 148, "output": 34, "witness": 0},
            "p2sh-p2wpkh": {"input": 91, "output": 32, "witness": 107},
            "p2wpkh": {"input": 68, "output": 31, "witness": 107},
            "p2tr": {"input": 57.5, "output": 43, "witness": 65},
        }

        sizes = type_sizes.get(address_type, type_sizes["p2wpkh"])

        input_vbytes = sizes["input"] * input_count
        output_vbytes = sizes["output"] * output_count
        witness_weight = sizes["witness"] * input_count * witness_discount
        total_vbytes = round(overhead + input_vbytes + output_vbytes + witness_weight)

        fees_1 = rpc.estimatesmartfee(1)
        fees_6 = rpc.estimatesmartfee(6)
        fees_144 = rpc.estimatesmartfee(144)

        # Fetch BTC price for USD conversion
        btc_usd = None
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
            req = urllib.request.Request(url, headers={"User-Agent": "bitcoin-mcp"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                price_data = json.loads(resp.read(1_000_000))
            btc_usd = price_data.get("bitcoin", {}).get("usd")
        except Exception:
            pass  # USD conversion optional

        def calc_cost(fee_result):
            rate = fee_result.get("feerate", 0) * 100000  # BTC/kvB to sat/vB
            sats = round(rate * total_vbytes)
            cost = {"sat_per_vb": round(rate, 2), "total_sats": sats}
            if btc_usd:
                cost["usd"] = round((sats / 1e8) * btc_usd, 2)
            return cost

        next_block = calc_cost(fees_1)
        one_hour = calc_cost(fees_6)
        one_day = calc_cost(fees_144)

        result = {
            "tx_size_vbytes": total_vbytes,
            "address_type": address_type,
            "inputs": input_count,
            "outputs": output_count,
            "btc_usd": btc_usd,
            "estimates": {
                "next_block": next_block,
                "one_hour": one_hour,
                "one_day": one_day,
            },
        }

        # Calculate savings from waiting
        if next_block["total_sats"] > 0 and one_day["total_sats"] > 0:
            saved_sats = next_block["total_sats"] - one_day["total_sats"]
            result["savings_by_waiting_1_day"] = {
                "sats": saved_sats,
                "pct": round((saved_sats / next_block["total_sats"]) * 100, 1),
            }
            if btc_usd:
                result["savings_by_waiting_1_day"]["usd"] = round((saved_sats / 1e8) * btc_usd, 2)

        return json.dumps(result)
    except Exception as e:
        hint = _connection_hint(e)
        return json.dumps({"error": str(e), "hint": hint})


# ============================================================
# MINING (3 tools)
# ============================================================


@mcp.tool()
def get_mining_info() -> str:
    """Get mining info: difficulty, network hashrate, current block size."""
    info = get_rpc().getmininginfo()
    return json.dumps(info)


@mcp.tool()
def analyze_next_block() -> str:
    """Predict next block: transactions, weight utilization, miner revenue, fee percentiles, top-fee txs."""
    data = _analyze_next_block(get_rpc())
    # Convert tuples to lists for JSON serialization
    if "top_5" in data:
        data["top_5"] = [
            {"txid": txid, "fee_rate": rate, "fee_sats": fee}
            for txid, rate, fee in data["top_5"]
        ]
    return json.dumps(data)


@mcp.tool()
def get_mining_pool_rankings() -> str:
    """Get top 10 Bitcoin mining pools by hashrate share over the last week. Returns pool name, percentage of total hashrate, and block count. Use this to understand mining centralization and pool dominance."""
    try:
        url = "https://mempool.space/api/v1/mining/pools/1w"
        req = urllib.request.Request(url, headers={"User-Agent": "bitcoin-mcp"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read(1_000_000))
        pools = data.get("pools", [])
        total_blocks = data.get("blockCount", 0)
        top_10 = []
        for p in pools[:10]:
            share_pct = round((p["blockCount"] / total_blocks) * 100, 2) if total_blocks > 0 else 0
            top_10.append({
                "name": p.get("name", "Unknown"),
                "hashrate_share_pct": share_pct,
                "block_count": p["blockCount"],
            })
        return json.dumps({
            "period": "1w",
            "total_blocks": total_blocks,
            "top_10_pools": top_10,
            "source": "mempool.space",
        })
    except Exception as e:
        return json.dumps({"error": f"Mining pool fetch failed: {e}", "hint": "mempool.space API may be down. Try again shortly."})


# ============================================================
# UTXO SET (2 tools)
# ============================================================


@mcp.tool()
def get_utxo_set_info() -> str:
    """Get UTXO set statistics: total UTXOs, total supply, disk size. Note: this is a slow operation (1-2 minutes on local nodes, may vary on hosted API)."""
    info = get_rpc().gettxoutsetinfo()
    return json.dumps({
        "height": info["height"],
        "txouts": info["txouts"],
        "total_amount": info["total_amount"],
        "disk_size": info["disk_size"],
        "hash_serialized_2": info.get("hash_serialized_2", ""),
    })


@mcp.tool()
def get_block_count() -> str:
    """Get current block height (lightweight, fast)."""
    height = get_rpc().getblockcount()
    return json.dumps({"height": height})


# ============================================================
# AI DEVELOPER TOOLS (9 tools)
# ============================================================


@mcp.tool()
def get_situation_summary() -> str:
    """Get a quick Bitcoin briefing: price, fees, mempool, and chain tip in one call. Use this as your first call to understand current conditions — replaces calling 5+ tools separately."""
    try:
        rpc = get_rpc()

        fees = rpc.estimatesmartfee(1)
        fees_6 = rpc.estimatesmartfee(6)
        fees_144 = rpc.estimatesmartfee(144)
        mempool = rpc.getmempoolinfo()
        blockchain = rpc.getblockchaininfo()

        next_block_rate = round(fees.get("feerate", 0) * 100000, 2)
        hour_rate = round(fees_6.get("feerate", 0) * 100000, 2)
        day_rate = round(fees_144.get("feerate", 0) * 100000, 2)

        # Fetch BTC price
        btc_usd = None
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
            req = urllib.request.Request(url, headers={"User-Agent": "bitcoin-mcp"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                price_data = json.loads(resp.read(1_000_000))
            btc = price_data.get("bitcoin", {})
            btc_usd = btc.get("usd")
            btc_24h_change = round(btc.get("usd_24h_change", 0), 2)
        except Exception:
            btc_24h_change = None

        # Typical tx cost in USD (140 vB native segwit)
        typical_cost_sats = round(next_block_rate * 140)
        typical_cost_usd = round((typical_cost_sats / 1e8) * btc_usd, 2) if btc_usd else None

        summary = {
            "btc_usd": btc_usd,
            "btc_24h_change_pct": btc_24h_change,
            "height": blockchain.get("blocks"),
            "chain": blockchain.get("chain"),
            "sync_progress_pct": round(blockchain.get("verificationprogress", 0) * 100, 2),
            "fees_sat_per_vb": {
                "next_block": next_block_rate,
                "hour": hour_rate,
                "day": day_rate,
            },
            "typical_tx_cost": {
                "sats": typical_cost_sats,
                "usd": typical_cost_usd,
            },
            "mempool": {
                "tx_count": mempool.get("size", 0),
                "size_mb": round(mempool.get("bytes", 0) / 1_000_000, 2),
                "min_fee_sat_vb": round(mempool.get("mempoolminfee", 0) * 100000, 2),
            },
        }
        return json.dumps(summary)
    except Exception as e:
        hint = _connection_hint(e)
        return json.dumps({"error": str(e), "hint": hint})


@mcp.tool()
def describe_rpc_command(command: str) -> str:
    """Get structured help for a Bitcoin RPC command: description, arguments, examples.

    Args:
        command: RPC command name (e.g. "getblock", "sendrawtransaction")
    """
    try:
        help_text = get_rpc().help(command)
    except Exception as e:
        return json.dumps({"error": str(e)})
    lines = help_text.strip().split("\n")
    description_lines = []
    arguments = []
    examples = []
    section = "description"
    for line in lines[1:]:  # skip first line (command signature)
        if line.strip().lower().startswith("argument"):
            section = "arguments"
        elif line.strip().lower().startswith("example"):
            section = "examples"
        if section == "description":
            description_lines.append(line)
        elif section == "arguments":
            arguments.append(line)
        elif section == "examples":
            examples.append(line)
    return json.dumps({
        "command": command,
        "signature": lines[0] if lines else command,
        "description": "\n".join(description_lines).strip(),
        "arguments": "\n".join(arguments).strip(),
        "examples": "\n".join(examples).strip(),
    })


@mcp.tool()
def list_rpc_commands() -> str:
    """List all available RPC commands grouped by category."""
    try:
        help_text = get_rpc().help()
    except Exception as e:
        return json.dumps({"error": str(e)})
    categories: dict[str, list[str]] = {}
    current_category = "uncategorized"
    for line in help_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("=="):
            current_category = line.strip("= ")
            categories[current_category] = []
        elif current_category:
            categories.setdefault(current_category, []).append(line.split()[0])
    return json.dumps(categories)


@mcp.tool()
def search_blockchain(query: str) -> str:
    """Smart search: auto-detects if query is a txid, block hash, block height, or address and returns the right data.

    Args:
        query: A txid (64 hex), block hash (64 hex starting with 0000), block height (number), or Bitcoin address
    """
    query = query.strip()
    # Block height (pure digits)
    if query.isdigit():
        try:
            analysis = _analyze_block(get_rpc(), query)
            return analysis.model_dump_json()
        except Exception as e:
            return json.dumps({"error": f"Block lookup failed: {e}"})
    # 64 hex chars — block hash or txid
    if re.fullmatch(r"[0-9a-fA-F]{64}", query):
        if query.startswith("0000"):
            try:
                analysis = _analyze_block(get_rpc(), query)
                return analysis.model_dump_json()
            except Exception:
                pass  # fall through to txid
        try:
            analysis = _analyze_transaction(get_rpc(), query)
            return analysis.model_dump_json()
        except Exception as e:
            return json.dumps({"error": f"Transaction lookup failed: {e}"})
    # Address validation
    try:
        result = get_rpc().validateaddress(query)
        if result.get("isvalid"):
            return json.dumps(result)
    except Exception:
        pass
    return json.dumps({"error": f"Could not identify query: {query!r}. Provide a txid, block hash, block height, or address."})


@mcp.tool()
def explain_script(hex_script: str) -> str:
    """Decode a Bitcoin Script hex and break down the opcodes.

    Args:
        hex_script: Script in hex format
    """
    try:
        result = get_rpc().decodescript(hex_script)
    except Exception as e:
        return json.dumps({"error": str(e)})
    if "asm" in result:
        result["opcodes"] = result["asm"].split()
    return json.dumps(result)


@mcp.tool()
def get_address_utxos(address: str) -> str:
    """Scan the UTXO set for all unspent outputs belonging to an address. Note: scans full UTXO set, may take minutes.

    Args:
        address: Bitcoin address to scan
    """
    try:
        result = get_rpc().scantxoutset("start", [f"addr({address})"])
    except Exception as e:
        return json.dumps({"error": str(e)})
    return json.dumps(result)


@mcp.tool()
def validate_address(address: str) -> str:
    """Validate a Bitcoin address and return its type (legacy/segwit/taproot), network, and script info. Use this to check if an address is valid before sending, or to identify what kind of address you're looking at.

    Args:
        address: Bitcoin address to validate (any format: P2PKH, P2SH, P2WPKH, P2WSH, P2TR)
    """
    try:
        result = get_rpc().validateaddress(address)
    except Exception as e:
        return json.dumps({"error": str(e)})
    addr_type = "unknown"
    if address.startswith("1"):
        addr_type = "P2PKH (legacy)"
    elif address.startswith("3"):
        addr_type = "P2SH (script hash)"
    elif address.startswith("bc1q") and len(address) == 42:
        addr_type = "P2WPKH (native segwit)"
    elif address.startswith("bc1q") and len(address) == 62:
        addr_type = "P2WSH (native segwit script)"
    elif address.startswith("bc1p"):
        addr_type = "P2TR (taproot)"
    elif address.startswith("tb1") or address.startswith("bcrt1"):
        addr_type = "testnet/regtest"
    result["address_type_classification"] = addr_type
    return json.dumps(result)


@mcp.tool()
def get_difficulty_adjustment() -> str:
    """Calculate difficulty adjustment progress: blocks into epoch, blocks remaining, estimated time, and projected adjustment."""
    try:
        info = get_rpc().getblockchaininfo()
        height = info["blocks"]
        blocks_into_epoch = height % 2016
        blocks_remaining = 2016 - blocks_into_epoch
        epoch_start_height = height - blocks_into_epoch
        epoch_start_hash = get_rpc().getblockhash(epoch_start_height)
        epoch_start_header = get_rpc().getblockheader(epoch_start_hash)
        current_hash = get_rpc().getblockhash(height)
        current_header = get_rpc().getblockheader(current_hash)
        elapsed_secs = current_header["time"] - epoch_start_header["time"]
        expected_secs = blocks_into_epoch * 600
        if blocks_into_epoch > 0:
            secs_per_block = elapsed_secs / blocks_into_epoch
            est_remaining_secs = blocks_remaining * secs_per_block
            est_adjustment_pct = ((expected_secs / elapsed_secs) - 1) * 100 if elapsed_secs > 0 else 0
        else:
            secs_per_block = 600
            est_remaining_secs = blocks_remaining * 600
            est_adjustment_pct = 0
    except Exception as e:
        return json.dumps({"error": str(e)})
    return json.dumps({
        "current_height": height,
        "epoch_start_height": epoch_start_height,
        "blocks_into_epoch": blocks_into_epoch,
        "blocks_remaining": blocks_remaining,
        "elapsed_seconds": elapsed_secs,
        "expected_seconds": expected_secs,
        "avg_block_time_seconds": round(secs_per_block, 1),
        "est_remaining_seconds": round(est_remaining_secs),
        "est_remaining_hours": round(est_remaining_secs / 3600, 1),
        "est_adjustment_pct": round(est_adjustment_pct, 2),
        "difficulty": info["difficulty"],
    })


@mcp.tool()
def compare_blocks(height1: int, height2: int) -> str:
    """Compare block statistics between two block heights side by side.

    Args:
        height1: First block height
        height2: Second block height
    """
    try:
        stats1 = get_rpc().getblockstats(height1)
        stats2 = get_rpc().getblockstats(height2)
    except Exception as e:
        return json.dumps({"error": str(e)})
    compare_keys = [
        "total_fee", "avgfee", "medianfee", "maxfee", "minfee",
        "total_weight", "total_size", "txs", "subsidy",
        "avgfeerate", "mediantime",
    ]
    comparison = {}
    for key in compare_keys:
        v1 = stats1.get(key)
        v2 = stats2.get(key)
        if v1 is None and v2 is None:
            continue
        entry = {"block_1": v1, "block_2": v2}
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            entry["delta"] = v2 - v1
        comparison[key] = entry
    return json.dumps({
        "height_1": height1,
        "height_2": height2,
        "comparison": comparison,
    })


# ============================================================
# PRICE & SUPPLY (4 tools)
# ============================================================


@mcp.tool()
def get_btc_price() -> str:
    """Get current BTC/USD price from CoinGecko (free, no API key). Returns price, 24h change, and market cap. Use this to convert sat/vB fees into dollar amounts."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
        req = urllib.request.Request(url, headers={"User-Agent": "bitcoin-mcp"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read(1_000_000))
        btc = data.get("bitcoin", {})
        return json.dumps({
            "usd": btc.get("usd"),
            "usd_24h_change_pct": round(btc.get("usd_24h_change", 0), 2),
            "usd_market_cap": btc.get("usd_market_cap"),
            "source": "coingecko",
        })
    except Exception as e:
        return json.dumps({"error": f"Price fetch failed: {e}", "hint": "CoinGecko may be rate-limiting. Try again in 30 seconds."})


@mcp.tool()
def get_supply_info() -> str:
    """Get Bitcoin supply data: circulating supply, max supply, inflation rate, subsidy per block, and next halving estimate."""
    try:
        rpc = get_rpc()
        info = rpc.getblockchaininfo()
        height = info["blocks"]

        # Calculate current subsidy
        halvings = height // 210_000
        subsidy_btc = 50.0 / (2 ** halvings)

        # Supply calculation (approximate from subsidy schedule)
        total_mined = 0.0
        for h in range(halvings):
            total_mined += 210_000 * (50.0 / (2 ** h))
        blocks_in_current_era = height - (halvings * 210_000)
        total_mined += blocks_in_current_era * subsidy_btc

        # Next halving
        next_halving_height = (halvings + 1) * 210_000
        blocks_until_halving = next_halving_height - height
        est_days_until_halving = round(blocks_until_halving * 10 / 60 / 24)

        # Annual inflation rate
        blocks_per_year = 365.25 * 24 * 6  # ~52,560
        annual_new_btc = blocks_per_year * subsidy_btc
        inflation_rate_pct = round((annual_new_btc / total_mined) * 100, 3) if total_mined > 0 else 0

        return json.dumps({
            "circulating_supply_btc": round(total_mined, 8),
            "max_supply_btc": 21_000_000,
            "pct_mined": round((total_mined / 21_000_000) * 100, 2),
            "current_subsidy_btc": subsidy_btc,
            "halvings_completed": halvings,
            "current_height": height,
            "next_halving_height": next_halving_height,
            "blocks_until_halving": blocks_until_halving,
            "est_days_until_halving": est_days_until_halving,
            "annual_inflation_rate_pct": inflation_rate_pct,
        })
    except Exception as e:
        hint = _connection_hint(e)
        return json.dumps({"error": str(e), "hint": hint})


@mcp.tool()
def get_halving_countdown() -> str:
    """Get a focused countdown to the next Bitcoin halving: blocks remaining, estimated date, and subsidy change."""
    try:
        rpc = get_rpc()
        height = rpc.getblockcount()
        halvings = height // 210_000
        current_subsidy = 50.0 / (2 ** halvings)
        next_subsidy = 50.0 / (2 ** (halvings + 1))
        next_halving_height = (halvings + 1) * 210_000
        blocks_remaining = next_halving_height - height

        # Estimate time using recent block rate
        try:
            stats = rpc.getchaintxstats(2016)
            secs_per_block = stats.get("window_interval", 600 * 2016) / stats.get("window_block_count", 2016)
        except Exception:
            secs_per_block = 600  # fallback to 10 min

        est_seconds = blocks_remaining * secs_per_block
        est_days = round(est_seconds / 86400)

        return json.dumps({
            "current_height": height,
            "next_halving_height": next_halving_height,
            "blocks_remaining": blocks_remaining,
            "est_days_remaining": est_days,
            "current_subsidy_btc": current_subsidy,
            "next_subsidy_btc": next_subsidy,
            "subsidy_reduction_pct": 50.0,
        })
    except Exception as e:
        hint = _connection_hint(e)
        return json.dumps({"error": str(e), "hint": hint})


@mcp.tool()
def get_market_sentiment() -> str:
    """Get Bitcoin Fear & Greed Index: current value (0-100), classification (Extreme Fear/Fear/Neutral/Greed/Extreme Greed), and 7-day history. Use this to gauge market sentiment alongside price data."""
    try:
        url = "https://api.alternative.me/fng/?limit=7"
        req = urllib.request.Request(url, headers={"User-Agent": "bitcoin-mcp"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read(1_000_000))
        entries = data.get("data", [])
        if not entries:
            return json.dumps({"error": "No data returned from Fear & Greed API"})
        current = entries[0]
        history = []
        for e in entries:
            history.append({
                "value": int(e["value"]),
                "classification": e["value_classification"],
                "timestamp": e["timestamp"],
            })
        return json.dumps({
            "current_value": int(current["value"]),
            "classification": current["value_classification"],
            "history_7d": history,
            "source": "alternative.me",
        })
    except Exception as e:
        return json.dumps({"error": f"Fear & Greed fetch failed: {e}", "hint": "api.alternative.me may be down. Try again shortly."})


# ============================================================
# LIGHTNING (1 tool)
# ============================================================


@mcp.tool()
def decode_bolt11_invoice(invoice: str) -> str:
    """Decode a BOLT11 Lightning invoice without external dependencies.

    Parses the human-readable part to extract network, amount, and timestamp.
    Does NOT verify the signature or parse tagged fields beyond basic extraction.

    Args:
        invoice: BOLT11 payment request string (starts with lnbc, lntb, or lnbcrt)
    """
    invoice = invoice.strip().lower()
    # Validate prefix
    if not invoice.startswith("ln"):
        return json.dumps({"error": "Not a BOLT11 invoice (must start with 'ln')"})

    # Find the last '1' separator between human-readable part and data
    sep_idx = invoice.rfind("1")
    if sep_idx < 2:
        return json.dumps({"error": "Invalid BOLT11 format: no separator found"})

    hrp = invoice[:sep_idx]
    data_part = invoice[sep_idx + 1:]

    # Parse network prefix
    if hrp.startswith("lnbcrt"):
        network = "regtest"
        amount_str = hrp[6:]
    elif hrp.startswith("lntbs"):
        network = "signet"
        amount_str = hrp[5:]
    elif hrp.startswith("lntb"):
        network = "testnet"
        amount_str = hrp[4:]
    elif hrp.startswith("lnbc"):
        network = "mainnet"
        amount_str = hrp[4:]
    else:
        network = "unknown"
        amount_str = ""

    # Parse amount with multiplier
    amount_btc = None
    multipliers = {"m": 0.001, "u": 0.000001, "n": 0.000000001, "p": 0.000000000001}
    if amount_str:
        if amount_str[-1] in multipliers:
            try:
                amount_btc = float(amount_str[:-1]) * multipliers[amount_str[-1]]
            except ValueError:
                amount_btc = None
        else:
            try:
                amount_btc = float(amount_str)
            except ValueError:
                amount_btc = None

    # Decode timestamp from data part using bech32 charset
    bech32_charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    charset_map = {c: i for i, c in enumerate(bech32_charset)}
    timestamp = None
    if len(data_part) >= 7:
        try:
            # First 7 chars of data = 35-bit timestamp
            ts_val = 0
            for ch in data_part[:7]:
                ts_val = ts_val * 32 + charset_map[ch]
            timestamp = ts_val
        except (KeyError, ValueError):
            timestamp = None

    result = {
        "network": network,
        "hrp": hrp,
        "amount_btc": amount_btc,
        "amount_sats": round(amount_btc * 1e8) if amount_btc is not None else None,
        "timestamp": timestamp,
        "data_length": len(data_part),
    }
    return json.dumps(result)


# ============================================================
# WALLET (1 tool)
# ============================================================


@mcp.tool()
def generate_keypair(address_type: str = "bech32", include_private_key: bool = False) -> str:
    """Generate a new Bitcoin address via the connected node's wallet. Requires a local node with a wallet loaded — not available when using the hosted Satoshi API.

    SECURITY: Private keys are redacted by default because AI provider tool responses may be logged. Set include_private_key=True only if you understand the risk — the key will appear in your conversation history and should be considered potentially compromised for high-value use.

    Args:
        address_type: Address type — "legacy" (P2PKH), "p2sh-segwit" (P2SH-P2WPKH), "bech32" (P2WPKH, default), or "bech32m" (P2TR taproot)
        include_private_key: If True, include the WIF private key in the response. Defaults to False for security.
    """
    try:
        rpc = get_rpc()
        if isinstance(rpc, _SatoshiRPC):
            return json.dumps({
                "error": "generate_keypair requires a local Bitcoin node with a wallet loaded. "
                         "It is not available when using the hosted Satoshi API.",
                "hint": "Run Bitcoin Core locally with a wallet, or use a dedicated wallet tool for key generation.",
            })
        address = rpc.getnewaddress("", address_type)
        addr_info = rpc.getaddressinfo(address)

        result = {
            "address": address,
            "public_key_hex": addr_info.get("pubkey"),
            "address_type": address_type,
            "is_mine": addr_info.get("ismine", False),
        }

        if include_private_key:
            try:
                privkey = rpc.dumpprivkey(address)
            except Exception:
                privkey = None  # Watch-only or descriptor wallet without private keys
            result["private_key_wif"] = privkey
            result["security_warning"] = (
                "This private key is now in your conversation history. "
                "Store it securely and consider this key potentially compromised for high-value use."
            )
        else:
            result["private_key_wif"] = (
                "[REDACTED — set include_private_key=true to reveal. "
                "WARNING: will be visible in conversation history]"
            )

        return json.dumps(result)
    except Exception as e:
        hint = _connection_hint(e)
        msg = str(e)
        if "no wallet" in msg.lower() or "wallet" in msg.lower():
            hint = "No wallet loaded. Create or load a wallet first: bitcoin-cli createwallet \"mywallet\""
        return json.dumps({"error": msg, "hint": hint})


# ============================================================
# RESOURCES (static data endpoints)
# ============================================================


def _connection_hint(error: Exception) -> str:
    """Return human-readable troubleshooting tips for common RPC errors."""
    msg = str(error).lower()
    api_tip = (
        " bitcoin-mcp automatically falls back to the free hosted Satoshi API "
        "(https://bitcoinsapi.com) when no local node is available — "
        "check your internet connection if both are failing."
    )
    if "no bitcoin node connection" in msg or "no rpc credentials" in msg:
        return (
            "No Bitcoin node detected and the hosted Satoshi API is unreachable. "
            "Check your internet connection, or install Bitcoin Core with 'server=1' in bitcoin.conf."
        )
    if "satoshi api" in msg or "cannot reach" in msg:
        return (
            "Cannot reach the hosted Satoshi API. Check your internet connection. "
            "If you want to use a local node instead, install Bitcoin Core with 'server=1' in bitcoin.conf."
        )
    if isinstance(error, ConnectionRefusedError) or "connection refused" in msg:
        return (
            "Connection refused. If using a local node, check that Bitcoin Core is running "
            "and RPC is enabled (BITCOIN_RPC_HOST, BITCOIN_RPC_PORT, 'server=1' in bitcoin.conf)." + api_tip
        )
    if "401" in msg or "unauthorized" in msg or "authentication" in msg:
        return (
            "Authentication failed. Check BITCOIN_RPC_USER and BITCOIN_RPC_PASSWORD, "
            "or ensure BITCOIN_DATADIR points to the correct directory for cookie auth."
        )
    if "403" in msg or "forbidden" in msg:
        return (
            "Access forbidden. Check rpcallowip in bitcoin.conf if connecting remotely."
        )
    if isinstance(error, TimeoutError) or "timeout" in msg or "timed out" in msg:
        return (
            "Connection timed out. The node or API may be starting up, syncing, or unreachable. "
            "Check network connectivity and firewall rules."
        )
    if "name or service not known" in msg or "getaddrinfo" in msg:
        return (
            "Host not found. Check that BITCOIN_RPC_HOST is a valid hostname or IP address."
        )
    return f"Unexpected error: {error}. Check your connection.{api_tip}"


@mcp.resource("bitcoin://connection/status")
def resource_connection_status() -> str:
    """Connection status: mode (local node or hosted API), network, and whether the connection is working."""
    network = os.getenv("BITCOIN_NETWORK", "mainnet").lower()
    info = {
        "network": network,
        "connected": False,
    }
    try:
        rpc = get_rpc()
        if isinstance(rpc, _SatoshiRPC):
            info["mode"] = "hosted_api"
            info["api_url"] = rpc._url.replace("/api/v1/rpc", "")
        else:
            info["mode"] = "local_node"
            port_str = os.getenv("BITCOIN_RPC_PORT")
            info["host"] = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1")
            info["port"] = int(port_str) if port_str else NETWORK_PORTS.get(network, 8332)
        chain_info = rpc.getblockchaininfo()
        info["connected"] = True
        info["chain"] = chain_info.get("chain")
        info["blocks"] = chain_info.get("blocks")
    except Exception as e:
        info["error"] = str(e)
        info["hint"] = _connection_hint(e)
    return json.dumps(info)


@mcp.resource("bitcoin://node/status")
def resource_node_status() -> str:
    """Current status summary of the connected Bitcoin node (local or hosted API)."""
    status = _get_status(get_rpc())
    return status.model_dump_json()


@mcp.resource("bitcoin://fees/current")
def resource_current_fees() -> str:
    """Current fee estimates."""
    estimates = _get_fee_estimates(get_rpc())
    return json.dumps([e.model_dump() for e in estimates])


@mcp.resource("bitcoin://mempool/snapshot")
def resource_mempool_snapshot() -> str:
    """Current mempool summary."""
    summary = _analyze_mempool(get_rpc())
    return summary.model_dump_json()


@mcp.resource("bitcoin://protocol/script-opcodes")
def resource_script_opcodes() -> str:
    """Common Bitcoin Script opcodes reference."""
    return json.dumps({
        "constants": {
            "OP_0": "Push empty byte array (false)",
            "OP_1": "Push the number 1 (true)",
            "OP_2-OP_16": "Push the number 2-16",
        },
        "flow_control": {
            "OP_IF": "Execute next block if top stack value is true",
            "OP_ELSE": "Execute if preceding OP_IF was not executed",
            "OP_ENDIF": "End if/else block",
            "OP_VERIFY": "Remove top stack item; fail if false",
            "OP_RETURN": "Mark transaction output as unspendable",
        },
        "stack": {
            "OP_DUP": "Duplicate top stack item",
            "OP_DROP": "Remove top stack item",
            "OP_SWAP": "Swap top two stack items",
            "OP_TOALTSTACK": "Move top item to alt stack",
            "OP_FROMALTSTACK": "Move top alt stack item to main stack",
        },
        "crypto": {
            "OP_CHECKSIG": "Verify signature against public key",
            "OP_CHECKMULTISIG": "Verify m-of-n multisig",
            "OP_HASH160": "SHA-256 then RIPEMD-160",
            "OP_SHA256": "SHA-256 hash",
            "OP_RIPEMD160": "RIPEMD-160 hash",
            "OP_HASH256": "Double SHA-256",
        },
        "arithmetic": {
            "OP_ADD": "Add top two items",
            "OP_EQUAL": "Push true if top two items are equal",
            "OP_EQUALVERIFY": "Same as OP_EQUAL then OP_VERIFY",
        },
        "locktime": {
            "OP_CHECKLOCKTIMEVERIFY": "Fail if locktime not reached (BIP 65)",
            "OP_CHECKSEQUENCEVERIFY": "Fail if relative locktime not reached (BIP 112)",
        },
    })


@mcp.resource("bitcoin://protocol/address-types")
def resource_address_types() -> str:
    """Bitcoin address types and their properties."""
    return json.dumps([
        {"type": "P2PKH", "prefix": "1", "example_prefix": "1A1z...", "length": "25-34", "witness_version": None, "script_type": "pubkeyhash", "bip": "BIP 13", "description": "Legacy pay-to-public-key-hash"},
        {"type": "P2SH", "prefix": "3", "example_prefix": "3J98...", "length": "34", "witness_version": None, "script_type": "scripthash", "bip": "BIP 16", "description": "Pay-to-script-hash (often wraps multisig or SegWit)"},
        {"type": "P2WPKH", "prefix": "bc1q", "example_prefix": "bc1q...", "length": "42", "witness_version": 0, "script_type": "witness_v0_keyhash", "bip": "BIP 84/141", "description": "Native SegWit pay-to-witness-public-key-hash"},
        {"type": "P2WSH", "prefix": "bc1q", "example_prefix": "bc1q...", "length": "62", "witness_version": 0, "script_type": "witness_v0_scripthash", "bip": "BIP 141", "description": "Native SegWit pay-to-witness-script-hash"},
        {"type": "P2TR", "prefix": "bc1p", "example_prefix": "bc1p...", "length": "62", "witness_version": 1, "script_type": "witness_v1_taproot", "bip": "BIP 86/341", "description": "Taproot pay-to-taproot"},
    ])


@mcp.resource("bitcoin://protocol/sighash-types")
def resource_sighash_types() -> str:
    """Bitcoin signature hash types reference."""
    return json.dumps([
        {"name": "SIGHASH_ALL", "value": "0x01", "description": "Sign all inputs and outputs (default)"},
        {"name": "SIGHASH_NONE", "value": "0x02", "description": "Sign all inputs, no outputs (anyone can set outputs)"},
        {"name": "SIGHASH_SINGLE", "value": "0x03", "description": "Sign all inputs, only the output with same index"},
        {"name": "SIGHASH_ALL|ANYONECANPAY", "value": "0x81", "description": "Sign one input and all outputs"},
        {"name": "SIGHASH_NONE|ANYONECANPAY", "value": "0x82", "description": "Sign one input, no outputs"},
        {"name": "SIGHASH_SINGLE|ANYONECANPAY", "value": "0x83", "description": "Sign one input and matching output"},
        {"name": "SIGHASH_DEFAULT (Taproot)", "value": "0x00", "description": "Taproot default, equivalent to SIGHASH_ALL but with different digest algorithm (BIP 341)"},
    ])


# ============================================================
# PROMPTS (reusable analysis templates)
# ============================================================


@mcp.prompt()
def analyze_fee_environment() -> str:
    """Analyze the current Bitcoin fee environment and make a send/wait recommendation."""
    return (
        "Use get_fee_estimates and analyze_mempool to assess the current Bitcoin "
        "fee environment. Report: current congestion level, fee rates for different "
        "urgencies, mempool depth by fee bucket, and a clear recommendation on "
        "whether to send now or wait."
    )


@mcp.prompt()
def investigate_transaction(txid: str) -> str:
    """Deep-dive investigation of a specific Bitcoin transaction."""
    return (
        f"Investigate Bitcoin transaction {txid}. Use analyze_transaction to decode it fully. "
        "Report: what type of transaction is this (payment, consolidation, inscription, etc.), "
        "the fee rate and whether it overpaid, script types used, whether it uses SegWit/Taproot, "
        "and any notable features (inscriptions, large number of inputs/outputs, etc.)."
    )


@mcp.prompt()
def monitor_mempool_fees(threshold_sat_vb: int = 20) -> str:
    """Monitor mempool and alert when fees drop below a threshold."""
    return (
        f"Continuously monitor the Bitcoin mempool fee environment. Use analyze_mempool "
        f"and get_fee_estimates to track fee rates. Alert when the next-block fee rate "
        f"drops below {threshold_sat_vb} sat/vB. Report current congestion, fee buckets, "
        f"and whether it's a good time to broadcast a transaction."
    )


@mcp.prompt()
def taproot_adoption_report(num_blocks: int = 100) -> str:
    """Analyze Taproot (P2TR) adoption trends over recent blocks."""
    return (
        f"Analyze Taproot adoption over the last {num_blocks} blocks. Use analyze_block "
        f"on a sample of blocks (e.g. every 10th block) to track the percentage of "
        f"Taproot (P2TR) transactions. Report the trend, current adoption rate, and "
        f"compare with SegWit adoption. Provide context on what this means for Bitcoin."
    )


@mcp.prompt()
def network_health_report() -> str:
    """Generate a comprehensive Bitcoin network health report."""
    return (
        "Generate a comprehensive Bitcoin network health report. Use these tools:\n"
        "1. get_node_status — sync state, version\n"
        "2. get_blockchain_info — chain stats, softforks\n"
        "3. get_peer_info — connectivity, peer diversity\n"
        "4. get_mining_info — hashrate, difficulty\n"
        "5. get_difficulty_adjustment — epoch progress\n"
        "6. analyze_mempool — congestion assessment\n"
        "7. get_fee_estimates — fee market state\n\n"
        "Synthesize into a report covering: chain health, network connectivity, "
        "mining security, fee market conditions, and any warnings or anomalies."
    )


@mcp.prompt()
def track_transaction(txid: str) -> str:
    """Track a transaction from mempool to confirmation."""
    return (
        f"Track Bitcoin transaction {txid}. First, try get_mempool_entry to check if "
        f"it's unconfirmed. If in mempool, report its fee rate, position estimate, and "
        f"ancestors (get_mempool_ancestors). Then use analyze_transaction for full details. "
        f"If confirmed, report the block it's in and confirmations. Assess whether the "
        f"fee rate was appropriate and estimate when it will confirm if still pending."
    )


# ============================================================
# INDEXED ADDRESS (4 tools — requires blockchain indexer)
# ============================================================


def _query_indexed_api(path: str) -> dict:
    """Query the Satoshi API indexed endpoints.

    Returns parsed JSON on success, or an error dict on failure.
    """
    api_url = os.getenv("SATOSHI_API_URL", _DEFAULT_API_URL).rstrip("/")
    url = f"{api_url}/api/v1/indexed/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "bitcoin-mcp"})
    api_key = os.getenv("SATOSHI_API_KEY")
    if api_key:
        req.add_header("X-API-Key", api_key)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read(10_000_000))
    except urllib.error.HTTPError as e:
        body = e.read(10_000).decode(errors="replace")
        try:
            return json.loads(body)
        except Exception:
            return {"error": f"HTTP {e.code}: {body[:200]}"}
    except urllib.error.URLError as e:
        return {"error": f"Indexer unavailable: {e.reason}. The blockchain indexer may not be running — address history requires ENABLE_INDEXER=true on the Satoshi API."}


def _query_mempool_space(path: str) -> dict:
    """Query mempool.space API as fallback for address data.

    Returns parsed JSON on success, or an error dict on failure.
    """
    url = f"https://mempool.space/api/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "bitcoin-mcp"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read(10_000_000))
    except urllib.error.HTTPError as e:
        body = e.read(10_000).decode(errors="replace")
        return {"error": f"mempool.space HTTP {e.code}: {body[:200]}"}
    except urllib.error.URLError as e:
        return {"error": f"mempool.space unavailable: {e.reason}"}


@mcp.tool()
def get_address_balance(address: str) -> str:
    """Get the total balance, transaction count, and first/last seen times for a Bitcoin address.

    Uses the Satoshi API blockchain indexer when available, falls back to mempool.space.
    Returns total received, total sent, current balance, tx count, and timestamps.

    Args:
        address: Bitcoin address (any format: legacy, P2SH, bech32, bech32m)
    """
    result = _query_indexed_api(f"address/{address}/balance")
    if "error" not in result:
        return json.dumps(result)
    # Fallback to mempool.space
    data = _query_mempool_space(f"address/{address}")
    if "error" in data:
        return json.dumps(data)
    chain = data.get("chain_stats", {})
    mempool = data.get("mempool_stats", {})
    balance = {
        "source": "mempool.space",
        "address": address,
        "total_received": chain.get("funded_txo_sum", 0),
        "total_sent": chain.get("spent_txo_sum", 0),
        "balance": chain.get("funded_txo_sum", 0) - chain.get("spent_txo_sum", 0),
        "tx_count": chain.get("tx_count", 0),
        "unconfirmed_balance": mempool.get("funded_txo_sum", 0) - mempool.get("spent_txo_sum", 0),
        "unconfirmed_tx_count": mempool.get("tx_count", 0),
    }
    return json.dumps(balance)


@mcp.tool()
def get_address_history(address: str, offset: int = 0, limit: int = 25) -> str:
    """Get paginated transaction history for a Bitcoin address.

    Uses the Satoshi API blockchain indexer when available, falls back to mempool.space.
    Shows each transaction with block height, timestamp, and net value change for the address.
    Results are ordered newest-first.

    Args:
        address: Bitcoin address (any format)
        offset: Skip this many transactions (for pagination, default 0)
        limit: Max transactions to return (default 25, max 100)
    """
    limit = min(limit, 100)
    result = _query_indexed_api(f"address/{address}/txs?offset={offset}&limit={limit}")
    if "error" not in result:
        return json.dumps(result)
    # Fallback to mempool.space (returns last 50 txs, no offset support)
    txs = _query_mempool_space(f"address/{address}/txs")
    if isinstance(txs, dict) and "error" in txs:
        return json.dumps(txs)
    if not isinstance(txs, list):
        return json.dumps({"error": "Unexpected response from mempool.space"})
    # Apply offset/limit manually
    page = txs[offset:offset + limit]
    history = {
        "source": "mempool.space",
        "address": address,
        "total_available": len(txs),
        "offset": offset,
        "limit": limit,
        "transactions": [
            {
                "txid": tx.get("txid"),
                "block_height": tx.get("status", {}).get("block_height"),
                "block_time": tx.get("status", {}).get("block_time"),
                "confirmed": tx.get("status", {}).get("confirmed", False),
                "fee": tx.get("fee"),
                "size": tx.get("size"),
                "weight": tx.get("weight"),
            }
            for tx in page
        ],
    }
    return json.dumps(history)


@mcp.tool()
def get_indexed_transaction(txid: str) -> str:
    """Get enriched transaction details from the blockchain indexer.

    Unlike analyze_transaction (which uses raw RPC), this returns resolved input addresses,
    spent/unspent status for each output, and block context.
    Falls back to mempool.space when the indexer is unavailable.

    Args:
        txid: Transaction ID (64-character hex string)
    """
    result = _query_indexed_api(f"tx/{txid}")
    if "error" not in result:
        return json.dumps(result)
    # Fallback to mempool.space
    data = _query_mempool_space(f"tx/{txid}")
    if isinstance(data, dict) and "error" in data:
        return json.dumps(data)
    if isinstance(data, dict):
        data["source"] = "mempool.space"
    return json.dumps(data)


@mcp.tool()
def get_indexer_status() -> str:
    """Check the blockchain indexer sync progress.

    Returns current indexed height, chain tip, sync percentage, blocks/sec, and ETA.
    Use this to check if the indexer is running and how far along the initial sync is.
    """
    result = _query_indexed_api("status")
    return json.dumps(result)


# ============================================================
# REMOTE API (conditional — requires SATOSHI_API_URL)
# ============================================================

_satoshi_api_url = os.getenv("SATOSHI_API_URL")
if _satoshi_api_url:
    try:
        from bitcoin_mcp.l402_client import L402Client

        @mcp.tool()
        def query_remote_api(endpoint: str, params: str = "") -> str:
            """Query a remote Satoshi API instance, auto-paying with Lightning if needed.

            Requires SATOSHI_API_URL environment variable. Supports L402 micropayments.

            Args:
                endpoint: API path (e.g. "/api/v1/fees", "/api/v1/blocks/latest")
                params: Optional query parameters as key=value pairs separated by &
            """
            if not endpoint.startswith("/api/v1/"):
                return json.dumps({"error": "Invalid endpoint: must start with /api/v1/"})
            if ".." in endpoint:
                return json.dumps({"error": "Invalid endpoint: path traversal not allowed"})
            parsed_params = {}
            if params:
                for pair in params.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        parsed_params[k] = v
            try:
                with L402Client(_satoshi_api_url) as client:
                    result = client.get(endpoint, params=parsed_params or None)
                    return json.dumps(result)
            except Exception as e:
                return json.dumps({"error": str(e)})

        logger.info("Remote API tool registered (target: %s)", _satoshi_api_url)
    except ImportError:
        logger.info("L402 client not available — install bitcoin-mcp[l402] for remote API support")


# ============================================================
# Entry point
# ============================================================


def main():
    from bitcoin_mcp import __version__

    parser = argparse.ArgumentParser(description="Bitcoin MCP Server")
    parser.add_argument("--version", action="version", version=f"bitcoin-mcp {__version__}")
    parser.add_argument("--check", action="store_true", help="Test RPC connection and exit")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument("--host", default=None, help="Host for HTTP transports (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Port for HTTP transports (default: 8000)")
    args = parser.parse_args()

    if args.check:
        try:
            rpc = get_rpc()
            info = rpc.getblockchaininfo()
            mode = "Satoshi API" if isinstance(rpc, _SatoshiRPC) else "local node"
            print(f"OK — {mode}, {info.get('chain', 'unknown')} chain at height {info.get('blocks', '?')}")
        except Exception as e:
            print(f"Connection failed: {e}")
            hint = _connection_hint(e)
            print(f"Hint: {hint}")
            sys.exit(1)
        return

    # Eagerly initialize connection so startup logs show the mode
    try:
        rpc = get_rpc()
        mode = "Satoshi API" if isinstance(rpc, _SatoshiRPC) else "local node"
        logger.info("Starting Bitcoin MCP server (%s)...", mode)
    except Exception as e:
        logger.warning("Starting Bitcoin MCP server (connection will retry on first tool call: %s)", e)

    if args.host:
        mcp.settings.host = args.host
    if args.port:
        mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
