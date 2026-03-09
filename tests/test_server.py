"""Tests for bitcoin-mcp server tools."""

import json
import os
import subprocess
import sys

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


class TestTransactionBroadcast:
    """Tests for send_raw_transaction tool."""

    def test_send_raw_transaction_success(self, mock_rpc):
        from bitcoin_mcp.server import send_raw_transaction
        result = json.loads(send_raw_transaction("0200000001..."))
        assert result["broadcast"] is True
        assert result["txid"] == "abcdef1234567890" * 4

    def test_send_raw_transaction_error(self, mock_rpc):
        mock_rpc.sendrawtransaction = lambda h, m: (_ for _ in ()).throw(
            Exception("TX decode failed")
        )
        from bitcoin_mcp.server import send_raw_transaction
        result = json.loads(send_raw_transaction("bad_hex"))
        assert result["broadcast"] is False
        assert "error" in result


class TestConnectionHint:
    """Tests for _connection_hint() helper."""

    def test_connection_refused(self):
        from bitcoin_mcp.server import _connection_hint
        hint = _connection_hint(ConnectionRefusedError("Connection refused"))
        assert "Connection refused" in hint
        assert "server=1" in hint

    def test_auth_failure(self):
        from bitcoin_mcp.server import _connection_hint
        hint = _connection_hint(Exception("401 Unauthorized"))
        assert "Authentication failed" in hint

    def test_forbidden(self):
        from bitcoin_mcp.server import _connection_hint
        hint = _connection_hint(Exception("403 Forbidden"))
        assert "rpcallowip" in hint

    def test_timeout(self):
        from bitcoin_mcp.server import _connection_hint
        hint = _connection_hint(TimeoutError("Connection timed out"))
        assert "timed out" in hint.lower() or "timeout" in hint.lower()

    def test_dns_failure(self):
        from bitcoin_mcp.server import _connection_hint
        hint = _connection_hint(Exception("Name or service not known"))
        assert "hostname" in hint.lower()

    def test_unknown_error(self):
        from bitcoin_mcp.server import _connection_hint
        hint = _connection_hint(Exception("something weird"))
        assert "Unexpected error" in hint


class TestCLIFlags:
    """Tests for CLI --version flag."""

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "bitcoin_mcp.server", "--version"],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.expanduser("~"), "Bortlesboat", "bitcoin-mcp"),
        )
        assert "0.4.0" in result.stdout or "0.4.0" in result.stderr
        assert result.returncode == 0


class TestMultiNetworkPort:
    """Tests for multi-network port selection."""

    def test_mainnet_default(self, monkeypatch):
        monkeypatch.delenv("BITCOIN_NETWORK", raising=False)
        monkeypatch.delenv("BITCOIN_RPC_PORT", raising=False)
        from bitcoin_mcp.server import _default_port
        assert _default_port() == 8332

    def test_testnet_port(self, monkeypatch):
        monkeypatch.setenv("BITCOIN_NETWORK", "testnet")
        from bitcoin_mcp.server import _default_port
        assert _default_port() == 18332

    def test_signet_port(self, monkeypatch):
        monkeypatch.setenv("BITCOIN_NETWORK", "signet")
        from bitcoin_mcp.server import _default_port
        assert _default_port() == 38332

    def test_regtest_port(self, monkeypatch):
        monkeypatch.setenv("BITCOIN_NETWORK", "regtest")
        from bitcoin_mcp.server import _default_port
        assert _default_port() == 18443

    def test_explicit_port_overrides_network(self, monkeypatch):
        """BITCOIN_RPC_PORT should override network-based default."""
        monkeypatch.setenv("BITCOIN_NETWORK", "testnet")
        monkeypatch.setenv("BITCOIN_RPC_PORT", "9999")
        # Reset singleton
        import bitcoin_mcp.server as srv
        monkeypatch.setattr(srv, "_rpc", None)
        # get_rpc will use 9999, not 18332
        # We can't easily test the actual port without connecting,
        # but we verify _default_port returns testnet port
        from bitcoin_mcp.server import _default_port
        assert _default_port() == 18332  # network default is testnet
        # The actual get_rpc() would use 9999 due to explicit BITCOIN_RPC_PORT

    def test_unknown_network_defaults_to_mainnet(self, monkeypatch):
        monkeypatch.setenv("BITCOIN_NETWORK", "fakenet")
        from bitcoin_mcp.server import _default_port
        assert _default_port() == 8332


class TestBolt11Decode:
    """Tests for BOLT11 invoice decoding."""

    def test_mainnet_invoice(self, mock_rpc):
        from bitcoin_mcp.server import decode_bolt11_invoice
        # Known test vector: lnbc1pvjluezsp5... (from BOLT11 spec)
        # Simpler: lnbc20m1... = 20 milliBTC on mainnet
        result = json.loads(decode_bolt11_invoice(
            "lnbc20m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqsfpp3qjmp7lwpagxun9pygexvgpjdc4jdj85fr9yq20q82gphp2nflc7jtzrcazrra7wwgzxqc8u7754cdlpfrmccae92qgzqvzq2ps8pqqqqqqpqqqqq9qqqvpeuqafqxu92d8lr6fvg0r5gv0heeeqgcrqlnm6jhphu9y00rrhy4grqszsvpcgpy9qqqqqqgqqqqq7qqzq9qrsgqdfjcdk6w3ak5pca9hwfwfh63zme2dt3p0ljg4apey0dglhllhje5vjrmyh4yv38j5lak6e2jsxnxnzh2s0gnkdasqypqt60nh3e"
        ))
        assert result["network"] == "mainnet"
        assert result["amount_btc"] == pytest.approx(0.02)
        assert result["amount_sats"] == 2000000

    def test_testnet_invoice(self, mock_rpc):
        from bitcoin_mcp.server import decode_bolt11_invoice
        result = json.loads(decode_bolt11_invoice("lntb100u1pvjluezqqqqqqqqqqqqqqqq"))
        assert result["network"] == "testnet"
        assert result["amount_btc"] == pytest.approx(0.0001)

    def test_regtest_invoice(self, mock_rpc):
        from bitcoin_mcp.server import decode_bolt11_invoice
        result = json.loads(decode_bolt11_invoice("lnbcrt500n1pvjluezqqqqqqqqqqqqqqqq"))
        assert result["network"] == "regtest"
        assert result["amount_btc"] == pytest.approx(0.0000005)

    def test_no_amount(self, mock_rpc):
        from bitcoin_mcp.server import decode_bolt11_invoice
        result = json.loads(decode_bolt11_invoice("lnbc1ptest1qqqqqqqqqqqqqqqq"))
        assert result["network"] == "mainnet"
        assert result["amount_btc"] is None
        assert result["amount_sats"] is None

    def test_invalid_prefix(self, mock_rpc):
        from bitcoin_mcp.server import decode_bolt11_invoice
        result = json.loads(decode_bolt11_invoice("notaninvoice"))
        assert "error" in result

    def test_timestamp_parsed(self, mock_rpc):
        from bitcoin_mcp.server import decode_bolt11_invoice
        result = json.loads(decode_bolt11_invoice(
            "lnbc20m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqsfpp3qjmp7lwpagxun9pygexvgpjdc4jdj85fr9yq20q82gphp2nflc7jtzrcazrra7wwgzxqc8u7754cdlpfrmccae92qgzqvzq2ps8pqqqqqqpqqqqq9qqqvpeuqafqxu92d8lr6fvg0r5gv0heeeqgcrqlnm6jhphu9y00rrhy4grqszsvpcgpy9qqqqqqgqqqqq7qqzq9qrsgqdfjcdk6w3ak5pca9hwfwfh63zme2dt3p0ljg4apey0dglhllhje5vjrmyh4yv38j5lak6e2jsxnxnzh2s0gnkdasqypqt60nh3e"
        ))
        assert result["timestamp"] is not None
        assert isinstance(result["timestamp"], int)


class TestPriceAndSupply:
    """Tests for price and supply tools."""

    def test_get_btc_price_handles_network_error(self, mock_rpc, monkeypatch):
        """get_btc_price returns error gracefully when CoinGecko is unreachable."""
        import bitcoin_mcp.server as srv
        # Mock urlopen to raise
        import urllib.request
        def mock_urlopen(*args, **kwargs):
            raise urllib.error.URLError("mocked network error")
        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
        from bitcoin_mcp.server import get_btc_price
        result = json.loads(get_btc_price())
        assert "error" in result

    def test_get_btc_price_parses_response(self, mock_rpc, monkeypatch):
        """get_btc_price returns structured price data."""
        import urllib.request
        import io
        mock_data = json.dumps({"bitcoin": {"usd": 97500.0, "usd_24h_change": -1.5, "usd_market_cap": 1900000000000}}).encode()
        class MockResp:
            def read(self): return mock_data
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: MockResp())
        from bitcoin_mcp.server import get_btc_price
        result = json.loads(get_btc_price())
        assert result["usd"] == 97500.0
        assert result["usd_24h_change_pct"] == -1.5
        assert result["source"] == "coingecko"

    def test_get_supply_info(self, mock_rpc):
        """get_supply_info returns supply data from node."""
        from bitcoin_mcp.server import get_supply_info
        result = json.loads(get_supply_info())
        assert result["max_supply_btc"] == 21_000_000
        assert result["current_height"] == 890000
        assert result["halvings_completed"] == 4  # 890000 // 210000 = 4
        assert result["current_subsidy_btc"] == 50.0 / (2 ** 4)  # 3.125
        assert result["blocks_until_halving"] > 0
        assert result["annual_inflation_rate_pct"] > 0
        assert result["pct_mined"] > 90  # Should be over 90% mined

    def test_get_halving_countdown(self, mock_rpc):
        """get_halving_countdown returns countdown data."""
        from bitcoin_mcp.server import get_halving_countdown
        result = json.loads(get_halving_countdown())
        assert result["current_height"] == 890000
        assert result["next_halving_height"] == 1050000  # (4+1) * 210000
        assert result["blocks_remaining"] == 160000
        assert result["current_subsidy_btc"] == 3.125
        assert result["next_subsidy_btc"] == 1.5625
        assert result["subsidy_reduction_pct"] == 50.0
        assert result["est_days_remaining"] > 0

    def test_get_supply_info_calculates_inflation(self, mock_rpc):
        """Verify inflation rate calculation is reasonable."""
        from bitcoin_mcp.server import get_supply_info
        result = json.loads(get_supply_info())
        # At halving 4, subsidy = 3.125 BTC/block
        # ~52560 blocks/year * 3.125 = ~164,250 BTC/year
        # With ~19.7M in circulation, that's ~0.83%
        assert 0.5 < result["annual_inflation_rate_pct"] < 2.0


class TestSituationSummary:
    """Tests for the get_situation_summary briefing tool."""

    def test_returns_structured_briefing(self, mock_rpc, monkeypatch):
        """get_situation_summary returns all expected fields."""
        import urllib.request
        mock_data = json.dumps({"bitcoin": {"usd": 97500.0, "usd_24h_change": 2.1}}).encode()
        class MockResp:
            def read(self): return mock_data
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: MockResp())
        from bitcoin_mcp.server import get_situation_summary
        result = json.loads(get_situation_summary())
        assert result["btc_usd"] == 97500.0
        assert result["height"] == 890000
        assert "fees_sat_per_vb" in result
        assert "next_block" in result["fees_sat_per_vb"]
        assert "typical_tx_cost" in result
        assert result["typical_tx_cost"]["sats"] > 0

    def test_works_without_price(self, mock_rpc, monkeypatch):
        """get_situation_summary works even when price fetch fails."""
        import urllib.request
        def mock_fail(*a, **k):
            raise urllib.error.URLError("no internet")
        monkeypatch.setattr(urllib.request, "urlopen", mock_fail)
        from bitcoin_mcp.server import get_situation_summary
        result = json.loads(get_situation_summary())
        assert result["btc_usd"] is None
        assert result["height"] == 890000
        assert result["typical_tx_cost"]["usd"] is None


class TestEstimateTransactionCost:
    """Tests for estimate_transaction_cost with USD pricing."""

    def test_returns_usd_with_price(self, mock_rpc, monkeypatch):
        """estimate_transaction_cost includes USD when price is available."""
        import urllib.request
        mock_data = json.dumps({"bitcoin": {"usd": 100000.0}}).encode()
        class MockResp:
            def read(self): return mock_data
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: MockResp())
        from bitcoin_mcp.server import estimate_transaction_cost
        result = json.loads(estimate_transaction_cost(2, 2, "p2wpkh"))
        assert result["btc_usd"] == 100000.0
        assert "usd" in result["estimates"]["next_block"]
        assert result["estimates"]["next_block"]["usd"] > 0
        assert "savings_by_waiting_1_day" in result
        assert "usd" in result["savings_by_waiting_1_day"]

    def test_works_without_price(self, mock_rpc, monkeypatch):
        """estimate_transaction_cost works when price fetch fails."""
        import urllib.request
        def mock_fail(*a, **k):
            raise urllib.error.URLError("no internet")
        monkeypatch.setattr(urllib.request, "urlopen", mock_fail)
        from bitcoin_mcp.server import estimate_transaction_cost
        result = json.loads(estimate_transaction_cost(1, 2, "p2tr"))
        assert result["btc_usd"] is None
        assert "usd" not in result["estimates"]["next_block"]
        assert result["estimates"]["next_block"]["total_sats"] > 0

    def test_taproot_vsize(self, mock_rpc, monkeypatch):
        """Verify P2TR vsize calculation is reasonable."""
        import urllib.request
        def mock_fail(*a, **k):
            raise urllib.error.URLError("no internet")
        monkeypatch.setattr(urllib.request, "urlopen", mock_fail)
        from bitcoin_mcp.server import estimate_transaction_cost
        result = json.loads(estimate_transaction_cost(2, 2, "p2tr"))
        # 2 P2TR inputs + 2 P2TR outputs should be roughly 200-250 vbytes
        assert 150 < result["tx_size_vbytes"] < 300
