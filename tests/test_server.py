"""Tests for bitcoin-mcp server tools."""

import json
import pytest


class TestNodeNetwork:
    """Tests for node and network tools (get_peer_info, get_network_info)."""

    def test_get_peer_info(self, mock_rpc):
        from bitcoin_mcp.server import get_peer_info
        result = json.loads(get_peer_info())
        assert len(result) == 1
        assert result[0]["addr"] == "1.2.3.4:8333"
        assert result[0]["subver"] == "/Satoshi:27.0.0/"
        assert result[0]["pingtime"] == 0.05
        assert result[0]["connection_type"] == "outbound-full-relay"

    def test_get_peer_info_limits_to_20(self, mock_rpc):
        """Verify peer list is capped at 20 entries."""
        mock_rpc.getpeerinfo = lambda: [
            {"addr": f"10.0.0.{i}:8333", "subver": "/Satoshi:27.0.0/",
             "pingtime": 0.01 * i, "synced_blocks": 890000,
             "connection_type": "outbound-full-relay"}
            for i in range(30)
        ]
        from bitcoin_mcp.server import get_peer_info
        result = json.loads(get_peer_info())
        assert len(result) == 20

    def test_get_network_info(self, mock_rpc):
        from bitcoin_mcp.server import get_network_info
        result = json.loads(get_network_info())
        assert result["connections"] == 10
        assert result["version"] == 270000
        assert result["subversion"] == "/Satoshi:27.0.0/"
        assert result["connections_in"] == 2
        assert result["connections_out"] == 8
        assert result["relayfee"] == 0.00001
        assert result["warnings"] == ""


class TestBlockchain:
    """Tests for blockchain and block tools."""

    def test_get_blockchain_info(self, mock_rpc):
        from bitcoin_mcp.server import get_blockchain_info
        result = json.loads(get_blockchain_info())
        assert result["chain"] == "main"
        assert result["blocks"] == 890000
        assert result["headers"] == 890000
        assert result["pruned"] is False
        assert "taproot" in result["softforks"]

    def test_get_block_stats(self, mock_rpc):
        from bitcoin_mcp.server import get_block_stats
        result = json.loads(get_block_stats(890000))
        assert result["txs"] == 3500
        assert result["height"] == 890000
        assert result["totalfee"] == 50000000
        assert result["avgfeerate"] == 25

    def test_get_chain_tx_stats_default(self, mock_rpc):
        from bitcoin_mcp.server import get_chain_tx_stats
        result = json.loads(get_chain_tx_stats())
        assert result["txrate"] == 5.5
        assert result["txcount"] == 950000000

    def test_get_chain_tx_stats_custom_window(self, mock_rpc):
        from bitcoin_mcp.server import get_chain_tx_stats
        result = json.loads(get_chain_tx_stats(144))
        assert "txrate" in result

    def test_get_chain_tips(self, mock_rpc):
        from bitcoin_mcp.server import get_chain_tips
        result = json.loads(get_chain_tips())
        assert len(result) == 2
        assert result[0]["status"] == "active"
        assert result[1]["status"] == "valid-fork"

    def test_search_blocks(self, mock_rpc):
        from bitcoin_mcp.server import search_blocks
        result = json.loads(search_blocks(890000, 890002))
        assert len(result) == 3
        assert result[0]["height"] == 890000
        assert result[1]["height"] == 890001
        assert result[2]["height"] == 890002
        # Verify fields are extracted correctly
        assert result[0]["txs"] == 3500
        assert result[0]["total_fee"] == 50000000

    def test_search_blocks_too_many(self, mock_rpc):
        from bitcoin_mcp.server import search_blocks
        result = json.loads(search_blocks(1, 100))
        assert "error" in result
        assert "Maximum range" in result["error"]

    def test_search_blocks_invalid_range(self, mock_rpc):
        from bitcoin_mcp.server import search_blocks
        result = json.loads(search_blocks(100, 1))
        assert "error" in result
        assert "start_height" in result["error"]

    def test_search_blocks_single_block(self, mock_rpc):
        from bitcoin_mcp.server import search_blocks
        result = json.loads(search_blocks(890000, 890000))
        assert len(result) == 1
        assert result[0]["height"] == 890000


class TestMempool:
    """Tests for mempool tools."""

    def test_get_mempool_info(self, mock_rpc):
        from bitcoin_mcp.server import get_mempool_info
        result = json.loads(get_mempool_info())
        assert result["size"] == 15000
        assert result["bytes"] == 8500000
        assert result["maxmempool"] == 300000000
        assert result["mempoolminfee"] == 0.00001

    def test_get_mempool_entry(self, mock_rpc):
        from bitcoin_mcp.server import get_mempool_entry
        result = json.loads(get_mempool_entry("abc123"))
        assert result["vsize"] == 140
        assert result["weight"] == 561

    def test_get_mempool_ancestors(self, mock_rpc):
        from bitcoin_mcp.server import get_mempool_ancestors
        result = json.loads(get_mempool_ancestors("test_txid"))
        assert result["ancestor_count"] == 1
        assert result["txid"] == "test_txid"
        assert len(result["ancestors"]) == 1
        anc = result["ancestors"][0]
        assert anc["txid"] == "abc123def456"
        assert anc["vsize"] == 200

    def test_get_mempool_ancestors_error(self, mock_rpc):
        """Test that RPC errors are caught and returned as JSON."""
        mock_rpc.getmempoolancestors = lambda txid, verbose: (_ for _ in ()).throw(
            Exception("Transaction not in mempool")
        )
        from bitcoin_mcp.server import get_mempool_ancestors
        result = json.loads(get_mempool_ancestors("nonexistent"))
        assert "error" in result


class TestTransactions:
    """Tests for transaction tools."""

    def test_decode_raw_transaction(self, mock_rpc):
        from bitcoin_mcp.server import decode_raw_transaction
        result = json.loads(decode_raw_transaction("0200000001..."))
        assert result["version"] == 2
        assert result["locktime"] == 0
        assert len(result["vin"]) == 1
        assert len(result["vout"]) == 1

    def test_check_utxo_unspent(self, mock_rpc):
        from bitcoin_mcp.server import check_utxo
        result = json.loads(check_utxo("txid123", 0))
        assert result["spent"] is False
        assert result["utxo"]["value"] == 0.5
        assert result["utxo"]["confirmations"] == 10

    def test_check_utxo_spent(self, mock_rpc):
        from bitcoin_mcp.server import check_utxo
        result = json.loads(check_utxo("txid123", 1))
        assert result["spent"] is True
        assert "message" in result


class TestFees:
    """Tests for fee estimation tools."""

    def test_estimate_smart_fee(self, mock_rpc):
        from bitcoin_mcp.server import estimate_smart_fee
        result = json.loads(estimate_smart_fee(6))
        assert result["conf_target"] == 6
        assert result["fee_rate_btc_kvb"] == 0.00015
        assert result["fee_rate_sat_vb"] == pytest.approx(15.0)
        assert result["errors"] == []

    def test_estimate_smart_fee_next_block(self, mock_rpc):
        from bitcoin_mcp.server import estimate_smart_fee
        result = json.loads(estimate_smart_fee(1))
        assert result["conf_target"] == 1
        assert result["fee_rate_btc_kvb"] == 0.00025
        assert result["fee_rate_sat_vb"] == 25.0

    def test_estimate_smart_fee_low_priority(self, mock_rpc):
        from bitcoin_mcp.server import estimate_smart_fee
        result = json.loads(estimate_smart_fee(144))
        assert result["conf_target"] == 144
        assert result["fee_rate_btc_kvb"] == 0.00003
        assert result["fee_rate_sat_vb"] == 3.0


class TestMining:
    """Tests for mining tools."""

    def test_get_mining_info(self, mock_rpc):
        from bitcoin_mcp.server import get_mining_info
        result = json.loads(get_mining_info())
        assert result["blocks"] == 890000
        assert result["difficulty"] == 83148355189239.77
        assert result["networkhashps"] == 6.5e20
        assert result["pooledtx"] == 15000


class TestUTXOSet:
    """Tests for UTXO set and block count tools."""

    def test_get_block_count(self, mock_rpc):
        from bitcoin_mcp.server import get_block_count
        result = json.loads(get_block_count())
        assert result["height"] == 890000

    def test_get_utxo_set_info(self, mock_rpc):
        from bitcoin_mcp.server import get_utxo_set_info
        result = json.loads(get_utxo_set_info())
        assert result["txouts"] == 170000000
        assert result["total_amount"] == 19625000
        assert result["height"] == 890000
        assert result["disk_size"] == 12000000000


class TestDeveloperTools:
    """Tests for AI developer tools."""

    def test_describe_rpc_command(self, mock_rpc):
        from bitcoin_mcp.server import describe_rpc_command
        result = json.loads(describe_rpc_command("getblock"))
        assert result["command"] == "getblock"
        assert "signature" in result
        assert "getblock" in result["signature"]

    def test_describe_rpc_command_error(self, mock_rpc):
        mock_rpc.help = lambda cmd=None: (_ for _ in ()).throw(
            Exception("Unknown command")
        )
        from bitcoin_mcp.server import describe_rpc_command
        result = json.loads(describe_rpc_command("fakecmd"))
        assert "error" in result

    def test_list_rpc_commands(self, mock_rpc):
        from bitcoin_mcp.server import list_rpc_commands
        result = json.loads(list_rpc_commands())
        assert "Blockchain" in result
        assert "getblock" in result["Blockchain"]
        assert "Network" in result
        assert "getpeerinfo" in result["Network"]

    def test_validate_address_p2tr(self, mock_rpc):
        from bitcoin_mcp.server import validate_address
        result = json.loads(validate_address("bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0"))
        assert result["isvalid"] is True
        assert result["address_type_classification"] == "P2TR"

    def test_validate_address_p2pkh(self, mock_rpc):
        from bitcoin_mcp.server import validate_address
        result = json.loads(validate_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
        assert result["address_type_classification"] == "P2PKH"

    def test_validate_address_p2sh(self, mock_rpc):
        from bitcoin_mcp.server import validate_address
        result = json.loads(validate_address("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"))
        assert result["address_type_classification"] == "P2SH"

    def test_validate_address_p2wpkh(self, mock_rpc):
        from bitcoin_mcp.server import validate_address
        # P2WPKH: bc1q prefix, 42 chars total
        addr = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
        result = json.loads(validate_address(addr))
        assert result["address_type_classification"] == "P2WPKH"

    def test_explain_script(self, mock_rpc):
        from bitcoin_mcp.server import explain_script
        result = json.loads(explain_script("76a914abc12388ac"))
        assert "opcodes" in result
        assert "OP_DUP" in result["opcodes"]
        assert "OP_CHECKSIG" in result["opcodes"]
        assert result["type"] == "pubkeyhash"

    def test_explain_script_error(self, mock_rpc):
        mock_rpc.decodescript = lambda h: (_ for _ in ()).throw(
            Exception("Invalid script")
        )
        from bitcoin_mcp.server import explain_script
        result = json.loads(explain_script("bad"))
        assert "error" in result

    def test_get_difficulty_adjustment(self, mock_rpc):
        from bitcoin_mcp.server import get_difficulty_adjustment
        result = json.loads(get_difficulty_adjustment())
        assert "blocks_remaining" in result
        assert "est_adjustment_pct" in result
        assert result["current_height"] == 890000
        # 890000 % 2016 = 1200, so blocks_remaining = 816
        assert result["blocks_into_epoch"] == 890000 % 2016
        assert result["blocks_remaining"] == 2016 - (890000 % 2016)
        assert result["difficulty"] == 83148355189239.77

    def test_get_difficulty_adjustment_epoch_start(self, mock_rpc):
        """Test at exact epoch boundary (blocks_into_epoch == 0)."""
        mock_rpc.getblockchaininfo = lambda: {
            "chain": "main", "blocks": 2016 * 441,  # exactly on boundary
            "headers": 2016 * 441,
            "difficulty": 83148355189239.77,
            "verificationprogress": 0.9999999,
            "size_on_disk": 650000000000,
            "pruned": False, "softforks": {},
        }
        from bitcoin_mcp.server import get_difficulty_adjustment
        result = json.loads(get_difficulty_adjustment())
        assert result["blocks_into_epoch"] == 0
        assert result["blocks_remaining"] == 2016

    def test_compare_blocks(self, mock_rpc):
        from bitcoin_mcp.server import compare_blocks
        result = json.loads(compare_blocks(890000, 890001))
        assert result["height_1"] == 890000
        assert result["height_2"] == 890001
        assert "comparison" in result
        comp = result["comparison"]
        # Both blocks return same mock stats, so deltas should be 0
        assert comp["txs"]["block_1"] == 3500
        assert comp["txs"]["block_2"] == 3500
        assert comp["txs"]["delta"] == 0

    def test_compare_blocks_error(self, mock_rpc):
        mock_rpc.getblockstats = lambda h: (_ for _ in ()).throw(
            Exception("Block not found")
        )
        from bitcoin_mcp.server import compare_blocks
        result = json.loads(compare_blocks(1, 2))
        assert "error" in result

    def test_get_address_utxos(self, mock_rpc):
        from bitcoin_mcp.server import get_address_utxos
        result = json.loads(get_address_utxos("bc1qtest"))
        assert result["success"] is True
        assert result["txouts"] == 2
        assert result["total_amount"] == 1.5
        assert len(result["unspents"]) == 2

    def test_get_address_utxos_error(self, mock_rpc):
        mock_rpc.scantxoutset = lambda a, d: (_ for _ in ()).throw(
            Exception("Scan failed")
        )
        from bitcoin_mcp.server import get_address_utxos
        result = json.loads(get_address_utxos("invalid"))
        assert "error" in result

    def test_search_blockchain_address(self, mock_rpc):
        """search_blockchain with an address should validate it."""
        from bitcoin_mcp.server import search_blockchain
        result = json.loads(search_blockchain("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"))
        assert result["isvalid"] is True

    def test_search_blockchain_unknown(self, mock_rpc):
        """search_blockchain with garbage input returns an error."""
        mock_rpc.validateaddress = lambda addr: {"isvalid": False}
        from bitcoin_mcp.server import search_blockchain
        result = json.loads(search_blockchain("not-a-valid-query"))
        assert "error" in result
        assert "Could not identify" in result["error"]
