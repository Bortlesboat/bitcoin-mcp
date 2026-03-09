"""Shared test fixtures for bitcoin-mcp tests."""

import json
import pytest


class MockRPC:
    """Mock Bitcoin RPC client for testing."""

    def getblockchaininfo(self):
        return {
            "chain": "main",
            "blocks": 890000,
            "headers": 890000,
            "bestblockhash": "0000000000000000000320283a032748cef8227873ff4872689bf23f1cda83a5",
            "difficulty": 83148355189239.77,
            "time": 1710000000,
            "verificationprogress": 0.9999999,
            "size_on_disk": 650000000000,
            "pruned": False,
            "softforks": {
                "taproot": {"type": "bip9", "active": True, "height": 709632}
            },
        }

    def getpeerinfo(self):
        return [
            {
                "addr": "1.2.3.4:8333",
                "subver": "/Satoshi:27.0.0/",
                "pingtime": 0.05,
                "synced_blocks": 890000,
                "connection_type": "outbound-full-relay",
            }
        ]

    def getnetworkinfo(self):
        return {
            "version": 270000,
            "subversion": "/Satoshi:27.0.0/",
            "protocolversion": 70016,
            "connections": 10,
            "connections_in": 2,
            "connections_out": 8,
            "relayfee": 0.00001,
            "warnings": "",
        }

    def getblockcount(self):
        return 890000

    def getblockhash(self, height):
        return "0000000000000000000320283a032748cef8227873ff4872689bf23f1cda83a5"

    def getblockheader(self, blockhash):
        return {
            "hash": blockhash,
            "height": 890000,
            "time": 1710000000,
            "nTx": 3500,
        }

    def getblockstats(self, height):
        return {
            "height": height,
            "time": 1710000000,
            "txs": 3500,
            "totalfee": 50000000,
            "avgfee": 14285,
            "medianfee": 10000,
            "maxfee": 500000,
            "minfee": 1000,
            "avgfeerate": 25,
            "feerate_percentiles": [5, 10, 15, 25, 50],
            "total_weight": 3990000,
            "total_size": 1500000,
            "subsidy": 312500000,
            "mediantime": 1709999000,
        }

    def getchaintxstats(self, nblocks=2016):
        return {
            "time": 1710000000,
            "txcount": 950000000,
            "txrate": 5.5,
            "window_tx_count": 500000,
            "window_block_count": 2016,
            "window_interval": 2016 * 600,  # ~10 min/block
        }

    def getchaintips(self):
        return [
            {"height": 890000, "hash": "000000000000000000032028...", "branchlen": 0, "status": "active"},
            {"height": 889998, "hash": "000000000000000000041234...", "branchlen": 1, "status": "valid-fork"},
        ]

    def getmempoolinfo(self):
        return {
            "size": 15000,
            "bytes": 8500000,
            "usage": 45000000,
            "maxmempool": 300000000,
            "mempoolminfee": 0.00001,
            "minrelaytxfee": 0.00001,
        }

    def getmempoolentry(self, txid):
        return {
            "vsize": 140,
            "weight": 561,
            "time": 1710000000,
            "fees": {"base": 0.00002800},
        }

    def getmempoolancestors(self, txid, verbose=False):
        return {
            "abc123def456": {
                "vsize": 200,
                "fees": {"base": 0.00004000},
                "depends": [],
            }
        }

    def estimatesmartfee(self, conf_target):
        rates = {1: 0.00025, 3: 0.00020, 6: 0.00015, 25: 0.00008, 144: 0.00003}
        rate = rates.get(conf_target, 0.00010)
        return {"feerate": rate, "blocks": conf_target}

    def decoderawtransaction(self, hex_string):
        return {
            "txid": "abcdef1234567890" * 4,
            "version": 2,
            "locktime": 0,
            "vin": [{"txid": "prev_tx", "vout": 0}],
            "vout": [{"value": 0.5, "scriptPubKey": {"type": "witness_v1_taproot"}}],
        }

    def gettxout(self, txid, vout):
        if vout == 0:
            return {"value": 0.5, "confirmations": 10, "scriptPubKey": {"type": "witness_v0_keyhash"}}
        return None  # spent

    def getmininginfo(self):
        return {
            "blocks": 890000,
            "difficulty": 83148355189239.77,
            "networkhashps": 6.5e20,
            "pooledtx": 15000,
        }

    def gettxoutsetinfo(self):
        return {
            "height": 890000,
            "txouts": 170000000,
            "total_amount": 19625000,
            "disk_size": 12000000000,
            "hash_serialized_2": "abcdef",
        }

    def help(self, command=None):
        if command:
            return f"{command} arg1 arg2\nDescription of {command}.\nArguments:\n1. arg1 (string)\nExamples:\n> {command} example"
        return "== Blockchain ==\ngetblock\ngetblockcount\n\n== Network ==\ngetpeerinfo"

    def validateaddress(self, address):
        return {"isvalid": True, "address": address, "scriptPubKey": "76a914...88ac"}

    def decodescript(self, hex_script):
        return {"asm": "OP_DUP OP_HASH160 abc123 OP_EQUALVERIFY OP_CHECKSIG", "type": "pubkeyhash"}

    def getconnectioncount(self):
        return 10

    def getblock(self, blockhash, verbosity=1):
        coinbase_tx = {
            "txid": "coinbase_txid_0000",
            "vin": [{"coinbase": "03a8960d00"}],
            "vout": [{"value": 3.125, "scriptPubKey": {"type": "pubkey"}}],
        }
        normal_tx = {
            "txid": "normal_txid_1111",
            "size": 225,
            "vsize": 141,
            "weight": 561,
            "vin": [{"txid": "prev_input_txid", "vout": 0, "txinwitness": ["sig"]}],
            "vout": [{"value": 0.5, "n": 0, "scriptPubKey": {"type": "witness_v0_keyhash", "address": "bc1qtest"}}],
            "fee": 0.0000141,
        }
        return {
            "hash": blockhash,
            "height": 890000,
            "version": 536870912,
            "time": 1710000000,
            "size": 1500000,
            "weight": 3990000,
            "nTx": 2,
            "tx": [coinbase_tx, normal_tx] if verbosity >= 2 else ["coinbase_txid_0000", "normal_txid_1111"],
        }

    def getrawmempool(self, verbose=False):
        if not verbose:
            return ["mempool_tx_1", "mempool_tx_2", "mempool_tx_3"]
        return {
            "mempool_tx_1": {
                "vsize": 140, "size": 200, "weight": 560,
                "fees": {"base": 0.00003500},
                "fee": 0.00003500,
            },
            "mempool_tx_2": {
                "vsize": 250, "size": 300, "weight": 1000,
                "fees": {"base": 0.00001250},
                "fee": 0.00001250,
            },
            "mempool_tx_3": {
                "vsize": 180, "size": 220, "weight": 720,
                "fees": {"base": 0.00009000},
                "fee": 0.00009000,
            },
        }

    def getrawtransaction(self, txid, verbose=False):
        return {
            "txid": txid,
            "version": 2,
            "size": 225,
            "vsize": 141,
            "weight": 561,
            "locktime": 0,
            "vin": [{"txid": "prev_input_txid", "vout": 0, "txinwitness": ["sig"]}],
            "vout": [
                {"value": 0.5, "n": 0, "scriptPubKey": {"type": "witness_v0_keyhash", "address": "bc1qtest"}},
            ],
            "blockhash": "0000000000000000000320283a032748cef8227873ff4872689bf23f1cda83a5",
            "confirmations": 6,
        }

    def getblocktemplate(self, template_request=None):
        return {
            "height": 890001,
            "transactions": [
                {"txid": "tmpl_tx_1", "hash": "tmpl_tx_1", "fee": 5000, "weight": 600},
                {"txid": "tmpl_tx_2", "hash": "tmpl_tx_2", "fee": 3000, "weight": 400},
                {"txid": "tmpl_tx_3", "hash": "tmpl_tx_3", "fee": 8000, "weight": 800},
            ],
        }

    def sendrawtransaction(self, hex_string, max_fee_rate=0.10):
        return "abcdef1234567890" * 4

    def getnewaddress(self, label="", address_type="bech32"):
        types = {
            "legacy": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "p2sh-segwit": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
            "bech32": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
            "bech32m": "bc1p5cyxnuxmeuwuvkwfem96lqzszee2457nljwp6t",
        }
        return types.get(address_type, types["bech32"])

    def getaddressinfo(self, address):
        return {
            "address": address,
            "scriptPubKey": "0014751e76e8199196d454941c45d1b3a323f1433bd6",
            "ismine": True,
            "pubkey": "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798",
            "desc": "wpkh([d34db33f/84h/0h/0h]0279be667e...)#checksum",
            "hdkeypath": "m/84'/0'/0'/0/0",
        }

    def dumpprivkey(self, address):
        return "KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn"

    def scantxoutset(self, action, descriptors):
        return {
            "success": True,
            "txouts": 2,
            "total_amount": 1.5,
            "unspents": [
                {"txid": "abc", "vout": 0, "amount": 1.0},
                {"txid": "def", "vout": 1, "amount": 0.5},
            ],
        }


@pytest.fixture
def mock_rpc(monkeypatch):
    """Replace the RPC singleton and get_rpc() with a mock."""
    mock = MockRPC()
    import bitcoin_mcp.server as srv
    monkeypatch.setattr(srv, "_rpc", mock)
    monkeypatch.setattr(srv, "get_rpc", lambda: mock)
    return mock
