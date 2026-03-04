"""Bitcoin MCP Server — 20 tools for AI agents to query Bitcoin nodes."""

import json
import logging
import os
import sys

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
    "bitcoin-node",
    instructions=(
        "Query and analyze a local Bitcoin Core/Knots node. "
        "Provides mempool analysis, fee estimation, block inspection, "
        "transaction decoding with inscription detection, and mining insights."
    ),
)

# --- RPC connection (lazy singleton) ---

_rpc: BitcoinRPC | None = None


def get_rpc() -> BitcoinRPC:
    global _rpc
    if _rpc is None:
        _rpc = BitcoinRPC(
            host=os.getenv("BITCOIN_RPC_HOST", "127.0.0.1"),
            port=int(os.getenv("BITCOIN_RPC_PORT", "8332")),
            user=os.getenv("BITCOIN_RPC_USER"),
            password=os.getenv("BITCOIN_RPC_PASSWORD"),
            datadir=os.getenv("BITCOIN_DATADIR"),
        )
    return _rpc


# ============================================================
# NODE & NETWORK (3 tools)
# ============================================================


@mcp.tool()
def get_node_status() -> str:
    """Get Bitcoin node status: chain, height, sync progress, disk usage, connections, version."""
    status = _get_status(get_rpc())
    return status.model_dump_json(indent=2)


@mcp.tool()
def get_peer_info() -> str:
    """Get connected peer details: addresses, latency, services, version."""
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
    return json.dumps(summary, indent=2)


@mcp.tool()
def get_network_info() -> str:
    """Get network info: protocol version, relay fee, local addresses, warnings."""
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
    }, indent=2)


# ============================================================
# BLOCKCHAIN & BLOCKS (4 tools)
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
    }, indent=2)


@mcp.tool()
def analyze_block(height_or_hash: str) -> str:
    """Analyze a block: mining pool, SegWit/Taproot adoption, fee distribution, revenue.

    Args:
        height_or_hash: Block height (e.g. "939290") or block hash
    """
    analysis = _analyze_block(get_rpc(), height_or_hash)
    return analysis.model_dump_json(indent=2)


@mcp.tool()
def get_block_stats(height: int) -> str:
    """Get raw block statistics: median fee, total output, subsidy, weight, tx count.

    Args:
        height: Block height
    """
    stats = get_rpc().getblockstats(height)
    return json.dumps(stats, indent=2)


@mcp.tool()
def get_chain_tx_stats(nblocks: int = 2016) -> str:
    """Get transaction rate statistics over N blocks.

    Args:
        nblocks: Number of blocks to average over (default 2016 = ~2 weeks)
    """
    stats = get_rpc().getchaintxstats(nblocks)
    return json.dumps(stats, indent=2)


# ============================================================
# MEMPOOL (3 tools)
# ============================================================


@mcp.tool()
def analyze_mempool() -> str:
    """Analyze the mempool: tx count, fee buckets, congestion level, next-block minimum fee."""
    summary = _analyze_mempool(get_rpc())
    return summary.model_dump_json(indent=2)


@mcp.tool()
def get_mempool_entry(txid: str) -> str:
    """Get details of a specific unconfirmed transaction in the mempool.

    Args:
        txid: Transaction hash (64 hex characters)
    """
    entry = get_rpc().getmempoolentry(txid)
    return json.dumps(entry, indent=2)


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
    }, indent=2)


# ============================================================
# TRANSACTIONS (3 tools)
# ============================================================


@mcp.tool()
def analyze_transaction(txid: str) -> str:
    """Decode and analyze a transaction: inputs, outputs, fee rate, SegWit/Taproot flags, inscription detection.

    Args:
        txid: Transaction hash (64 hex characters). Requires txindex=1 for confirmed txs.
    """
    analysis = _analyze_transaction(get_rpc(), txid)
    return analysis.model_dump_json(indent=2)


@mcp.tool()
def decode_raw_transaction(hex_string: str) -> str:
    """Decode a raw transaction hex without looking up inputs.

    Args:
        hex_string: Raw transaction in hex format
    """
    result = get_rpc().decoderawtransaction(hex_string)
    return json.dumps(result, indent=2)


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
    return json.dumps({"spent": False, "utxo": result}, indent=2)


# ============================================================
# FEE ESTIMATION (3 tools)
# ============================================================


@mcp.tool()
def get_fee_estimates() -> str:
    """Get fee rate estimates for 1/3/6/25/144 block confirmation targets in sat/vB."""
    estimates = _get_fee_estimates(get_rpc())
    return json.dumps([e.model_dump() for e in estimates], indent=2)


@mcp.tool()
def get_fee_recommendation() -> str:
    """Get a plain-English fee recommendation based on current estimates."""
    estimates = _get_fee_estimates(get_rpc())
    rates = {e.conf_target: e.fee_rate_sat_vb for e in estimates if not e.errors}
    return fee_recommendation(rates)


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
    }, indent=2)


# ============================================================
# MINING (2 tools)
# ============================================================


@mcp.tool()
def get_mining_info() -> str:
    """Get mining info: difficulty, network hashrate, current block size."""
    info = get_rpc().getmininginfo()
    return json.dumps(info, indent=2)


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
    return json.dumps(data, indent=2)


# ============================================================
# UTXO SET (2 tools)
# ============================================================


@mcp.tool()
def get_utxo_set_info() -> str:
    """Get UTXO set statistics: total UTXOs, total supply, disk size. WARNING: Takes 1-2 minutes."""
    info = get_rpc().gettxoutsetinfo()
    return json.dumps({
        "height": info["height"],
        "txouts": info["txouts"],
        "total_amount": info["total_amount"],
        "disk_size": info["disk_size"],
        "hash_serialized_2": info.get("hash_serialized_2", ""),
    }, indent=2)


@mcp.tool()
def get_block_count() -> str:
    """Get current block height (lightweight, fast)."""
    height = get_rpc().getblockcount()
    return json.dumps({"height": height})


# ============================================================
# RESOURCES (static data endpoints)
# ============================================================


@mcp.resource("bitcoin://node/status")
def resource_node_status() -> str:
    """Current node status summary."""
    status = _get_status(get_rpc())
    return status.model_dump_json(indent=2)


@mcp.resource("bitcoin://fees/current")
def resource_current_fees() -> str:
    """Current fee estimates."""
    estimates = _get_fee_estimates(get_rpc())
    return json.dumps([e.model_dump() for e in estimates], indent=2)


@mcp.resource("bitcoin://mempool/snapshot")
def resource_mempool_snapshot() -> str:
    """Current mempool summary."""
    summary = _analyze_mempool(get_rpc())
    return summary.model_dump_json(indent=2)


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


# ============================================================
# Entry point
# ============================================================


def main():
    logger.info("Starting Bitcoin MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
