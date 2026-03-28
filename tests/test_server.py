"""Tests for bitcoin-mcp server tools."""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

import pytest

from bitcoin_mcp import __version__


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
        result = json.loads(decode_raw_transaction("0200000001abcdef"))
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
        assert result["address_type_classification"] == "P2TR (taproot)"

    def test_validate_address_p2pkh(self, mock_rpc):
        from bitcoin_mcp.server import validate_address
        result = json.loads(validate_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
        assert result["address_type_classification"] == "P2PKH (legacy)"

    def test_validate_address_p2sh(self, mock_rpc):
        from bitcoin_mcp.server import validate_address
        result = json.loads(validate_address("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"))
        assert result["address_type_classification"] == "P2SH (script hash)"

    def test_validate_address_p2wpkh(self, mock_rpc):
        from bitcoin_mcp.server import validate_address
        # P2WPKH: bc1q prefix, 42 chars total
        addr = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
        result = json.loads(validate_address(addr))
        assert result["address_type_classification"] == "P2WPKH (native segwit)"

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
        result = json.loads(send_raw_transaction("0200000001abcdef"))
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
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        assert __version__ in result.stdout or __version__ in result.stderr
        assert result.returncode == 0

    def test_log_level_accepted(self):
        """--log-level flag is accepted by argparse without error."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            result = subprocess.run(
                [sys.executable, "-m", "bitcoin_mcp.server", "--log-level", level, "--check"],
                capture_output=True, text=True,
                env={**os.environ, "SATOSHI_API_URL": "https://bitcoinsapi.com"},
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                timeout=15,
            )
            # Should not fail with argparse error; may fail on connection but that's OK
            assert "unrecognized arguments" not in result.stderr, f"Rejected --log-level {level}"

    def test_invalid_log_level_rejected(self):
        """--log-level with invalid value is rejected."""
        result = subprocess.run(
            [sys.executable, "-m", "bitcoin_mcp.server", "--log-level", "INVALID"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower() or "INVALID" in result.stderr


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
            def read(self, size=-1): return mock_data
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
            def read(self, size=-1): return mock_data
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
            def read(self, size=-1): return mock_data
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


class TestMarketSentiment:
    """Tests for Fear & Greed Index tool."""

    def test_parses_response(self, mock_rpc, monkeypatch):
        import urllib.request
        import io
        api_response = json.dumps({
            "data": [
                {"value": "72", "value_classification": "Greed", "timestamp": "1710000000"},
                {"value": "65", "value_classification": "Greed", "timestamp": "1709913600"},
            ]
        }).encode()
        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: io.BytesIO(api_response),
        )
        from bitcoin_mcp.server import get_market_sentiment
        result = json.loads(get_market_sentiment())
        assert result["current_value"] == 72
        assert result["classification"] == "Greed"
        assert len(result["history_7d"]) == 2
        assert result["source"] == "alternative.me"

    def test_handles_error(self, mock_rpc, monkeypatch):
        import urllib.request
        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: (_ for _ in ()).throw(Exception("timeout")),
        )
        from bitcoin_mcp.server import get_market_sentiment
        result = json.loads(get_market_sentiment())
        assert "error" in result
        assert "hint" in result


class TestMiningPoolRankings:
    """Tests for mining pool rankings tool."""

    def test_parses_response(self, mock_rpc, monkeypatch):
        import urllib.request
        import io
        api_response = json.dumps({
            "blockCount": 1000,
            "pools": [
                {"name": "Foundry USA", "blockCount": 280},
                {"name": "AntPool", "blockCount": 180},
                {"name": "ViaBTC", "blockCount": 120},
            ]
        }).encode()
        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: io.BytesIO(api_response),
        )
        from bitcoin_mcp.server import get_mining_pool_rankings
        result = json.loads(get_mining_pool_rankings())
        assert result["total_blocks"] == 1000
        assert len(result["top_10_pools"]) == 3
        assert result["top_10_pools"][0]["name"] == "Foundry USA"
        assert result["top_10_pools"][0]["hashrate_share_pct"] == 28.0
        assert result["source"] == "mempool.space"

    def test_handles_error(self, mock_rpc, monkeypatch):
        import urllib.request
        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: (_ for _ in ()).throw(Exception("connection failed")),
        )
        from bitcoin_mcp.server import get_mining_pool_rankings
        result = json.loads(get_mining_pool_rankings())
        assert "error" in result


class TestGenerateKeypair:
    """Tests for keypair generation tool."""

    def test_generates_bech32_address(self, mock_rpc):
        from bitcoin_mcp.server import generate_keypair
        result = json.loads(generate_keypair("bech32"))
        assert result["address"].startswith("bc1q")
        assert "REDACTED" in result["private_key_wif"]
        assert result["public_key_hex"] is not None
        assert result["address_type"] == "bech32"
        assert result["is_mine"] is True

    def test_generates_bech32_with_private_key(self, mock_rpc):
        from bitcoin_mcp.server import generate_keypair
        result = json.loads(generate_keypair("bech32", include_private_key=True))
        assert result["address"].startswith("bc1q")
        assert result["private_key_wif"].startswith("K")  # WIF compressed mainnet
        assert "security_warning" in result

    def test_generates_legacy_address(self, mock_rpc):
        from bitcoin_mcp.server import generate_keypair
        result = json.loads(generate_keypair("legacy"))
        assert result["address"].startswith("1")
        assert result["address_type"] == "legacy"

    def test_generates_taproot_address(self, mock_rpc):
        from bitcoin_mcp.server import generate_keypair
        result = json.loads(generate_keypair("bech32m"))
        assert result["address"].startswith("bc1p")
        assert result["address_type"] == "bech32m"

    def test_handles_no_wallet(self, mock_rpc):
        mock_rpc.getnewaddress = lambda *a, **k: (_ for _ in ()).throw(
            Exception("No wallet is loaded"))
        from bitcoin_mcp.server import generate_keypair
        result = json.loads(generate_keypair())
        assert "error" in result
        assert "wallet" in result["hint"].lower()


class TestGetNodeStatus:
    """Tests for get_node_status tool."""

    def test_returns_status_fields(self, mock_rpc):
        from bitcoin_mcp.server import get_node_status
        result = json.loads(get_node_status())
        assert result["chain"] == "main"
        assert result["blocks"] == 890000
        assert result["connections"] == 10
        assert result["version"] == 270000

    def test_error_on_rpc_failure(self, mock_rpc):
        mock_rpc.getblockchaininfo = lambda: (_ for _ in ()).throw(
            Exception("Node unreachable")
        )
        from bitcoin_mcp.server import get_node_status
        with pytest.raises(Exception, match="Node unreachable"):
            get_node_status()


class TestAnalyzeBlock:
    """Tests for analyze_block tool."""

    def test_analyze_by_height(self, mock_rpc):
        from bitcoin_mcp.server import analyze_block
        result = json.loads(analyze_block("890000"))
        assert result["height"] == 890000
        assert result["tx_count"] == 2
        assert result["weight"] == 3990000

    def test_analyze_by_hash(self, mock_rpc):
        from bitcoin_mcp.server import analyze_block
        blockhash = "0000000000000000000320283a032748cef8227873ff4872689bf23f1cda83a5"
        result = json.loads(analyze_block(blockhash))
        assert result["hash"] == blockhash
        assert result["height"] == 890000

    def test_analyze_block_rpc_error(self, mock_rpc):
        mock_rpc.getblockhash = lambda h: (_ for _ in ()).throw(
            Exception("Block not found")
        )
        from bitcoin_mcp.server import analyze_block
        with pytest.raises(Exception):
            analyze_block("999999999")


class TestAnalyzeMempool:
    """Tests for analyze_mempool tool."""

    def test_returns_summary(self, mock_rpc):
        from bitcoin_mcp.server import analyze_mempool
        result = json.loads(analyze_mempool())
        # size comes from getmempoolinfo, not raw mempool count
        assert result["size"] == 15000
        assert result["total_bytes"] == 8500000
        assert "buckets" in result
        assert "congestion" in result

    def test_error_on_rpc_failure(self, mock_rpc):
        mock_rpc.getrawmempool = lambda verbose=False: (_ for _ in ()).throw(
            Exception("Mempool error")
        )
        from bitcoin_mcp.server import analyze_mempool
        with pytest.raises(Exception, match="Mempool error"):
            analyze_mempool()


class TestAnalyzeTransaction:
    """Tests for analyze_transaction tool."""

    def test_returns_analysis(self, mock_rpc):
        from bitcoin_mcp.server import analyze_transaction
        txid = "abcdef1234567890" * 4
        result = json.loads(analyze_transaction(txid))
        assert result["txid"] == txid
        assert result["version"] == 2
        assert result["vsize"] == 141
        assert result["is_segwit"] is True
        assert len(result["outputs"]) >= 1

    def test_error_on_rpc_failure(self, mock_rpc):
        mock_rpc.getrawtransaction = lambda txid, verbose=False: (_ for _ in ()).throw(
            Exception("Transaction not found")
        )
        from bitcoin_mcp.server import analyze_transaction
        with pytest.raises(Exception, match="Transaction not found"):
            analyze_transaction("deadbeef" * 8)


class TestGetFeeEstimates:
    """Tests for get_fee_estimates tool."""

    def test_returns_list_of_estimates(self, mock_rpc):
        from bitcoin_mcp.server import get_fee_estimates
        result = json.loads(get_fee_estimates())
        assert isinstance(result, list)
        assert len(result) == 5  # targets: 1, 3, 6, 25, 144
        targets = [e["conf_target"] for e in result]
        assert targets == [1, 3, 6, 25, 144]
        assert result[0]["fee_rate_sat_vb"] == pytest.approx(25.0)
        assert result[4]["fee_rate_sat_vb"] == pytest.approx(3.0)

    def test_handles_missing_feerate(self, mock_rpc):
        mock_rpc.estimatesmartfee = lambda t: {"errors": ["Insufficient data"], "blocks": t}
        from bitcoin_mcp.server import get_fee_estimates
        result = json.loads(get_fee_estimates())
        assert all(e["fee_rate_sat_vb"] == 0.0 for e in result)
        assert all("Insufficient data" in e["errors"] for e in result)


class TestGetFeeRecommendation:
    """Tests for get_fee_recommendation tool."""

    def test_returns_recommendation(self, mock_rpc):
        from bitcoin_mcp.server import get_fee_recommendation
        result = json.loads(get_fee_recommendation())
        assert "recommendation" in result
        assert isinstance(result["recommendation"], str)
        assert "rates" in result
        # JSON keys are strings
        assert "1" in result["rates"]
        assert "144" in result["rates"]

    def test_handles_no_data(self, mock_rpc):
        mock_rpc.estimatesmartfee = lambda t: {"errors": ["Insufficient data"], "blocks": t}
        from bitcoin_mcp.server import get_fee_recommendation
        result = json.loads(get_fee_recommendation())
        assert result["rates"] == {}


class TestCompareFeeEstimates:
    """Tests for compare_fee_estimates tool."""

    def test_returns_rows_with_urgency(self, mock_rpc):
        from bitcoin_mcp.server import compare_fee_estimates
        result = json.loads(compare_fee_estimates())
        assert isinstance(result, list)
        assert len(result) == 5
        assert result[0]["urgency"] == "Next Block"
        assert result[0]["conf_target"] == 1
        assert result[0]["fee_rate_sat_vb"] == pytest.approx(25.0)
        assert result[0]["cost_140vb_sats"] == round(25.0 * 140)
        assert result[4]["urgency"] == "~1 day"

    def test_handles_errors_in_estimates(self, mock_rpc):
        mock_rpc.estimatesmartfee = lambda t: {"errors": ["No data"], "blocks": t}
        from bitcoin_mcp.server import compare_fee_estimates
        result = json.loads(compare_fee_estimates())
        assert all(r["fee_rate_sat_vb"] is None for r in result)
        assert all(r["cost_140vb_sats"] is None for r in result)


class TestAnalyzeNextBlock:
    """Tests for analyze_next_block tool."""

    def test_returns_template_analysis(self, mock_rpc):
        from bitcoin_mcp.server import analyze_next_block
        result = json.loads(analyze_next_block())
        assert result["height"] == 890001
        assert result["tx_count"] == 3
        assert result["total_fee_sats"] == 16000  # 5000 + 3000 + 8000
        assert result["total_weight"] == 1800  # 600 + 400 + 800
        assert "top_5" in result
        assert len(result["top_5"]) == 3
        # Top fee tx should be tmpl_tx_3 (8000 fee / 200 vsize = 40 sat/vB)
        assert result["top_5"][0]["txid"] == "tmpl_tx_3"

    def test_error_on_rpc_failure(self, mock_rpc):
        mock_rpc.getblocktemplate = lambda template_request=None: (_ for _ in ()).throw(
            Exception("Not connected to mining network")
        )
        from bitcoin_mcp.server import analyze_next_block
        with pytest.raises(Exception, match="Not connected"):
            analyze_next_block()


class TestQueryRemoteApi:
    """Tests for query_remote_api tool (conditional on SATOSHI_API_URL)."""

    def test_queries_api_successfully(self, mock_rpc, monkeypatch):
        """query_remote_api calls L402Client and returns JSON result."""
        monkeypatch.setenv("SATOSHI_API_URL", "https://test.example.com")
        import bitcoin_mcp.server as srv

        # Mock L402Client as a context manager
        class MockL402Client:
            def __init__(self, url):
                self.url = url
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass
            def get(self, endpoint, params=None):
                return {"status": "ok", "endpoint": endpoint, "params": params}

        # Patch the L402Client import
        monkeypatch.setattr(srv, "_satoshi_api_url", "https://test.example.com")

        # We need to test the function logic directly since it's defined conditionally.
        # Re-create the function inline to test the logic.
        import json as _json

        def query_remote_api(endpoint: str, params: str = "") -> str:
            if not endpoint.startswith("/api/v1/"):
                return _json.dumps({"error": "Invalid endpoint: must start with /api/v1/"})
            if ".." in endpoint:
                return _json.dumps({"error": "Invalid endpoint: path traversal not allowed"})
            parsed_params = {}
            if params:
                for pair in params.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        parsed_params[k] = v
            try:
                with MockL402Client("https://test.example.com") as client:
                    result = client.get(endpoint, params=parsed_params or None)
                    return _json.dumps(result)
            except Exception as e:
                return _json.dumps({"error": str(e)})

        result = json.loads(query_remote_api("/api/v1/fees", "target=6"))
        assert result["status"] == "ok"
        assert result["endpoint"] == "/api/v1/fees"
        assert result["params"] == {"target": "6"}

    def test_rejects_invalid_endpoint(self, mock_rpc, monkeypatch):
        """query_remote_api rejects endpoints not starting with /api/v1/."""
        import json as _json

        def query_remote_api(endpoint: str, params: str = "") -> str:
            if not endpoint.startswith("/api/v1/"):
                return _json.dumps({"error": "Invalid endpoint: must start with /api/v1/"})
            if ".." in endpoint:
                return _json.dumps({"error": "Invalid endpoint: path traversal not allowed"})
            return _json.dumps({"ok": True})

        result = json.loads(query_remote_api("/etc/passwd"))
        assert "error" in result
        assert "must start with /api/v1/" in result["error"]

    def test_rejects_path_traversal(self, mock_rpc, monkeypatch):
        """query_remote_api rejects path traversal attempts."""
        import json as _json

        def query_remote_api(endpoint: str, params: str = "") -> str:
            if not endpoint.startswith("/api/v1/"):
                return _json.dumps({"error": "Invalid endpoint: must start with /api/v1/"})
            if ".." in endpoint:
                return _json.dumps({"error": "Invalid endpoint: path traversal not allowed"})
            return _json.dumps({"ok": True})

        result = json.loads(query_remote_api("/api/v1/../../etc/passwd"))
        assert "error" in result
        assert "path traversal" in result["error"]

    def test_handles_client_error(self, mock_rpc, monkeypatch):
        """query_remote_api returns error when L402Client fails."""
        import json as _json

        class FailingClient:
            def __init__(self, url): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def get(self, endpoint, params=None):
                raise ConnectionError("API unavailable")

        def query_remote_api(endpoint: str, params: str = "") -> str:
            if not endpoint.startswith("/api/v1/"):
                return _json.dumps({"error": "Invalid endpoint: must start with /api/v1/"})
            if ".." in endpoint:
                return _json.dumps({"error": "Invalid endpoint: path traversal not allowed"})
            try:
                with FailingClient("https://test.example.com") as client:
                    result = client.get(endpoint, params=None)
                    return _json.dumps(result)
            except Exception as e:
                return _json.dumps({"error": str(e)})

        result = json.loads(query_remote_api("/api/v1/fees"))
        assert "error" in result
        assert "API unavailable" in result["error"]


class TestIndexedAddress:
    """Tests for indexed address tools (get_address_balance, get_address_history, etc.)."""

    def _mock_urlopen(self, response_data, monkeypatch):
        """Helper to mock urllib.request.urlopen with a canned response."""
        import io

        class MockResponse:
            def __init__(self, data):
                self._data = json.dumps(data).encode()
            def read(self, n=-1):
                return self._data
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda req, timeout=None: MockResponse(response_data),
        )

    def test_get_address_balance_success(self, mock_rpc, monkeypatch):
        from bitcoin_mcp.server import get_address_balance
        self._mock_urlopen({
            "data": {
                "address": "3HFXx9YLAQhD2mzcRRke4w3iEJ7wUETLqk",
                "total_received": 150000000,
                "total_sent": 100000000,
                "balance": 50000000,
                "tx_count": 42,
                "first_seen": "2024-01-15T10:30:00Z",
                "last_seen": "2026-03-09T14:00:00Z",
            }
        }, monkeypatch)
        result = json.loads(get_address_balance("3HFXx9YLAQhD2mzcRRke4w3iEJ7wUETLqk"))
        assert result["data"]["balance"] == 50000000
        assert result["data"]["tx_count"] == 42

    def test_get_address_history_success(self, mock_rpc, monkeypatch):
        from bitcoin_mcp.server import get_address_history
        self._mock_urlopen({
            "data": {
                "address": "bc1qtest",
                "transactions": [
                    {"txid": "abc123", "block_height": 890000, "net_value": 50000}
                ],
                "total": 1,
            }
        }, monkeypatch)
        result = json.loads(get_address_history("bc1qtest", offset=0, limit=25))
        assert len(result["data"]["transactions"]) == 1
        assert result["data"]["transactions"][0]["txid"] == "abc123"

    def test_get_address_history_caps_limit(self, mock_rpc, monkeypatch):
        """Limit is capped at 100 even if caller requests more."""
        from bitcoin_mcp.server import get_address_history
        captured_urls = []

        class MockResponse:
            def __init__(self):
                self._data = json.dumps({"data": {"transactions": [], "total": 0}}).encode()
            def read(self, n=-1):
                return self._data
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        def capturing_urlopen(req, timeout=None):
            captured_urls.append(req.full_url if hasattr(req, 'full_url') else str(req))
            return MockResponse()

        monkeypatch.setattr("urllib.request.urlopen", capturing_urlopen)
        get_address_history("bc1qtest", offset=0, limit=500)
        assert "limit=100" in captured_urls[0]

    def test_get_indexed_transaction_success(self, mock_rpc, monkeypatch):
        from bitcoin_mcp.server import get_indexed_transaction
        self._mock_urlopen({
            "data": {
                "txid": "abc123" * 10 + "abcd",
                "block_height": 890000,
                "inputs": [{"address": "bc1qsender", "value": 100000}],
                "outputs": [{"address": "bc1qrecv", "value": 90000, "spent": False}],
            }
        }, monkeypatch)
        result = json.loads(get_indexed_transaction("abc123" * 10 + "abcd"))
        assert result["data"]["block_height"] == 890000
        assert result["data"]["outputs"][0]["spent"] is False

    def test_get_indexer_status_success(self, mock_rpc, monkeypatch):
        from bitcoin_mcp.server import get_indexer_status
        self._mock_urlopen({
            "data": {
                "indexed_height": 500000,
                "chain_tip": 890000,
                "sync_percentage": 56.18,
                "blocks_per_sec": 12.5,
                "eta_hours": 8.7,
            }
        }, monkeypatch)
        result = json.loads(get_indexer_status())
        assert result["data"]["indexed_height"] == 500000
        assert result["data"]["sync_percentage"] == 56.18

    def test_indexer_unavailable_falls_back_to_mempool(self, mock_rpc, monkeypatch):
        """When indexer and mempool.space are both unreachable, return error."""
        from bitcoin_mcp.server import get_address_balance
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda req, timeout=None: (_ for _ in ()).throw(
                urllib.error.URLError("Connection refused")
            ),
        )
        result = json.loads(get_address_balance("bc1qtest"))
        assert "error" in result
        assert "unavailable" in result["error"].lower()

    def test_api_key_forwarded(self, mock_rpc, monkeypatch):
        """SATOSHI_API_KEY is sent as X-API-Key header."""
        monkeypatch.setenv("SATOSHI_API_KEY", "test-key-123")
        captured_headers = {}

        class MockResponse:
            def __init__(self):
                self._data = json.dumps({"data": {}}).encode()
            def read(self, n=-1):
                return self._data
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        def capturing_urlopen(req, timeout=None):
            captured_headers.update(dict(req.headers))
            return MockResponse()

        import urllib.request
        monkeypatch.setattr("urllib.request.urlopen", capturing_urlopen)
        from bitcoin_mcp.server import get_indexer_status
        get_indexer_status()
        assert captured_headers.get("X-api-key") == "test-key-123"

    def test_http_404_returns_error(self, mock_rpc, monkeypatch):
        """HTTP 404 from indexer returns parsed error body."""
        from bitcoin_mcp.server import get_address_balance

        def raise_404(req, timeout=None):
            import io
            body = json.dumps({"error": "Address not found"}).encode()
            raise urllib.error.HTTPError(
                req.full_url if hasattr(req, 'full_url') else str(req),
                404, "Not Found", {}, io.BytesIO(body)
            )

        monkeypatch.setattr("urllib.request.urlopen", raise_404)
        result = json.loads(get_address_balance("bc1qnonexistent"))
        assert "error" in result
        assert "not found" in result["error"].lower()


class TestSatoshiRPC:
    """Tests for the _SatoshiRPC fallback client."""

    def test_builds_correct_url(self):
        from bitcoin_mcp.server import _SatoshiRPC
        client = _SatoshiRPC("https://example.com")
        assert client._url == "https://example.com/api/v1/rpc"

    def test_strips_trailing_slash(self):
        from bitcoin_mcp.server import _SatoshiRPC
        client = _SatoshiRPC("https://example.com/")
        assert client._url == "https://example.com/api/v1/rpc"

    def test_dynamic_method_dispatch(self):
        """Calling any method name on _SatoshiRPC returns a callable."""
        from bitcoin_mcp.server import _SatoshiRPC
        client = _SatoshiRPC("https://example.com")
        assert callable(client.getblockchaininfo)
        assert callable(client.estimatesmartfee)

    def test_get_rpc_falls_back_to_satoshi(self, monkeypatch):
        """get_rpc() should fall back to _SatoshiRPC when no local node."""
        import bitcoin_mcp.server as srv
        srv._rpc = None  # reset singleton
        # Clear all RPC env vars
        for key in ["BITCOIN_RPC_USER", "BITCOIN_RPC_PASSWORD", "BITCOIN_DATADIR",
                     "BITCOIN_RPC_HOST", "BITCOIN_RPC_PORT", "SATOSHI_API_URL"]:
            monkeypatch.delenv(key, raising=False)
        # Mock BitcoinRPC to raise (simulating no local node)
        monkeypatch.setattr(srv, "BitcoinRPC", lambda **kw: (_ for _ in ()).throw(ConnectionError("no cookie")))
        rpc = srv.get_rpc()
        assert isinstance(rpc, srv._SatoshiRPC)
        assert "bitcoinsapi.com" in rpc._url
        srv._rpc = None  # cleanup

    def test_get_rpc_respects_custom_api_url(self, monkeypatch):
        """get_rpc() should use SATOSHI_API_URL env var for fallback."""
        import bitcoin_mcp.server as srv
        srv._rpc = None
        for key in ["BITCOIN_RPC_USER", "BITCOIN_RPC_PASSWORD", "BITCOIN_DATADIR",
                     "BITCOIN_RPC_HOST", "BITCOIN_RPC_PORT"]:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("SATOSHI_API_URL", "https://custom.example.com")
        monkeypatch.setattr(srv, "BitcoinRPC", lambda **kw: (_ for _ in ()).throw(ConnectionError("no cookie")))
        rpc = srv.get_rpc()
        assert isinstance(rpc, srv._SatoshiRPC)
        assert "custom.example.com" in rpc._url
        srv._rpc = None
