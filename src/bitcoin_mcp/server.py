"""Bitcoin MCP Server — 32 tools for AI agents to query Bitcoin nodes."""

import json
import logging
import os
import re
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


@mcp.tool()
def get_chain_tips() -> str:
    """Get chain tips: active chain, forks, and stale branches. Useful for detecting chain splits."""
    tips = get_rpc().getchaintips()
    return json.dumps(tips, indent=2)


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
    return json.dumps(results, indent=2)


# ============================================================
# MEMPOOL (4 tools)
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
# FEE ESTIMATION (4 tools)
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
    return json.dumps(rows, indent=2)


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
# AI DEVELOPER TOOLS (8 tools)
# ============================================================


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
    }, indent=2)


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
    return json.dumps(categories, indent=2)


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
            return analysis.model_dump_json(indent=2)
        except Exception as e:
            return json.dumps({"error": f"Block lookup failed: {e}"})
    # 64 hex chars — block hash or txid
    if re.fullmatch(r"[0-9a-fA-F]{64}", query):
        if query.startswith("0000"):
            try:
                analysis = _analyze_block(get_rpc(), query)
                return analysis.model_dump_json(indent=2)
            except Exception:
                pass  # fall through to txid
        try:
            analysis = _analyze_transaction(get_rpc(), query)
            return analysis.model_dump_json(indent=2)
        except Exception as e:
            return json.dumps({"error": f"Transaction lookup failed: {e}"})
    # Address validation
    try:
        result = get_rpc().validateaddress(query)
        if result.get("isvalid"):
            return json.dumps(result, indent=2)
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
    return json.dumps(result, indent=2)


@mcp.tool()
def get_address_utxos(address: str) -> str:
    """Scan the UTXO set for all unspent outputs belonging to an address. WARNING: Scans full UTXO set, may take minutes.

    Args:
        address: Bitcoin address to scan
    """
    try:
        result = get_rpc().scantxoutset("start", [f"addr({address})"])
    except Exception as e:
        return json.dumps({"error": str(e)})
    return json.dumps(result, indent=2)


@mcp.tool()
def validate_address(address: str) -> str:
    """Validate a Bitcoin address and classify its type (P2PKH, P2SH, P2WPKH, P2WSH, P2TR).

    Args:
        address: Bitcoin address to validate
    """
    try:
        result = get_rpc().validateaddress(address)
    except Exception as e:
        return json.dumps({"error": str(e)})
    addr_type = "unknown"
    if address.startswith("1"):
        addr_type = "P2PKH"
    elif address.startswith("3"):
        addr_type = "P2SH"
    elif address.startswith("bc1q") and len(address) == 42:
        addr_type = "P2WPKH"
    elif address.startswith("bc1q") and len(address) == 62:
        addr_type = "P2WSH"
    elif address.startswith("bc1p"):
        addr_type = "P2TR"
    result["address_type_classification"] = addr_type
    return json.dumps(result, indent=2)


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
    }, indent=2)


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
    }, indent=2)


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
    }, indent=2)


@mcp.resource("bitcoin://protocol/address-types")
def resource_address_types() -> str:
    """Bitcoin address types and their properties."""
    return json.dumps([
        {"type": "P2PKH", "prefix": "1", "example_prefix": "1A1z...", "length": "25-34", "witness_version": None, "script_type": "pubkeyhash", "bip": "BIP 13", "description": "Legacy pay-to-public-key-hash"},
        {"type": "P2SH", "prefix": "3", "example_prefix": "3J98...", "length": "34", "witness_version": None, "script_type": "scripthash", "bip": "BIP 16", "description": "Pay-to-script-hash (often wraps multisig or SegWit)"},
        {"type": "P2WPKH", "prefix": "bc1q", "example_prefix": "bc1q...", "length": "42", "witness_version": 0, "script_type": "witness_v0_keyhash", "bip": "BIP 84/141", "description": "Native SegWit pay-to-witness-public-key-hash"},
        {"type": "P2WSH", "prefix": "bc1q", "example_prefix": "bc1q...", "length": "62", "witness_version": 0, "script_type": "witness_v0_scripthash", "bip": "BIP 141", "description": "Native SegWit pay-to-witness-script-hash"},
        {"type": "P2TR", "prefix": "bc1p", "example_prefix": "bc1p...", "length": "62", "witness_version": 1, "script_type": "witness_v1_taproot", "bip": "BIP 86/341", "description": "Taproot pay-to-taproot"},
    ], indent=2)


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
    ], indent=2)


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
            parsed_params = {}
            if params:
                for pair in params.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        parsed_params[k] = v
            try:
                with L402Client(_satoshi_api_url) as client:
                    result = client.get(endpoint, params=parsed_params or None)
                    return json.dumps(result, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})

        logger.info("Remote API tool registered (target: %s)", _satoshi_api_url)
    except ImportError:
        logger.info("L402 client not available — install bitcoin-mcp[l402] for remote API support")


# ============================================================
# Entry point
# ============================================================


def main():
    logger.info("Starting Bitcoin MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
