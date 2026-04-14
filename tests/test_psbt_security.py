"""Tests for PSBT security analysis tools."""

import json


class TestPSBTSecurityAnalysis:
    """Tests for _psbt_analyze and its public tool wrappers."""

    @staticmethod
    def _srv():
        import bitcoin_mcp.server as srv

        return srv

    def test_invalid_hex_returns_error_dict(self):
        srv = self._srv()
        result = srv._psbt_analyze("ZZZZ")
        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid hex encoding" in result["error"]

    def test_empty_hex_returns_error(self):
        srv = self._srv()
        result = srv._psbt_analyze("")
        assert isinstance(result, dict)
        assert "error" in result

    def test_raw_bitcoin_tx_not_psbt(self):
        srv = self._srv()
        raw_tx = (
            "0200000001abcdef00000000000000000000000000ffffffff01e803000000000000"
            "1976a914d85c2b71d0060b09c8816b7b1f1c9aab79d9b7fe88ac00000000"
        )
        result = srv._psbt_analyze(raw_tx)
        assert "error" in result
        assert "magic" in result["error"].lower()

    def test_wrong_magic_rejected(self):
        srv = self._srv()
        result = srv._psbt_analyze("00000000000000000000000000")
        assert "error" in result

    def test_magic_only_is_error(self):
        srv = self._srv()
        result = srv._psbt_analyze("70736274ff")
        assert "error" in result

    def test_analyze_psbt_security_returns_string(self):
        srv = self._srv()
        result = srv.analyze_psbt_security("ZZZZ")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "error" in parsed

    def test_explain_inscription_returns_error_string_for_invalid(self):
        srv = self._srv()
        result = srv.explain_inscription_listing_security("ZZZZ")
        assert isinstance(result, str)
        assert "error" in result.lower() or "invalid" in result.lower()

    def test_analyze_psbt_always_returns_json_string(self):
        srv = self._srv()
        for bad_input in ["ZZZZ", "", "0000", "70736274ff"]:
            result = srv.analyze_psbt_security(bad_input)
            assert isinstance(result, str)
            json.loads(result)


class TestPSBTAnalysisInputValidation:
    """Tests for PSBT parsing helper behavior."""

    @staticmethod
    def _srv():
        import bitcoin_mcp.server as srv

        return srv

    def test_psbt_magic_bytes_correct(self):
        srv = self._srv()
        assert srv._PSBT_MAGIC == b"psbt\xff"

    def test_sighash_names_defined(self):
        srv = self._srv()
        assert srv._PSBT_SIGHASH_NAMES[0x01] == "SIGHASH_ALL"
        assert srv._PSBT_SIGHASH_NAMES[0x83] == "SIGHASH_SINGLE|ANYONECANPAY"
        assert srv._PSBT_SIGHASH_NAMES[0x81] == "SIGHASH_ALL|ANYONECANPAY"

    def test_varint_read_roundtrip(self):
        srv = self._srv()
        val, off = srv._psbt_read_varint(bytes([0x00, 0x00, 0x00]), 0)
        assert val == 0 and off == 1
        val, off = srv._psbt_read_varint(bytes([0xFC, 0x00, 0x00]), 0)
        assert val == 0xFC and off == 1
        val, off = srv._psbt_read_varint(bytes([0xFD, 0x01, 0x00, 0x00]), 0)
        assert val == 1 and off == 3
        val, off = srv._psbt_read_varint(
            bytes([0xFE, 0x01, 0x00, 0x00, 0x00, 0x00]), 0
        )
        assert val == 1 and off == 5
        val, off = srv._psbt_read_varint(
            bytes([0xFF, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), 0
        )
        assert val == 1 and off == 9

    def test_is_2of2_multisig_true(self):
        srv = self._srv()
        valid_script = bytes.fromhex("5221" + "11" * 33 + "21" + "22" * 33 + "52ae")
        assert len(valid_script) == 71
        assert srv._psbt_is_2of2_multisig(valid_script) is True

    def test_is_2of2_multisig_false_wrong_length(self):
        srv = self._srv()
        short_script = bytes.fromhex("5221" + "11" * 65 + "21" + "22" * 66 + "52ae")
        assert srv._psbt_is_2of2_multisig(short_script) is False
        long_script = bytes.fromhex("5221" + "11" * 66 + "21" + "22" * 66 + "52ae00")
        assert srv._psbt_is_2of2_multisig(long_script) is False

    def test_is_2of2_multisig_false_non_multisig(self):
        srv = self._srv()
        p2pkh = bytes.fromhex("76a914d85c2b71d0060b09c8816b7b1f1c9aab79d9b7fe88ac")
        assert srv._psbt_is_2of2_multisig(p2pkh) is False

    def test_psbt_parse_map_empty(self):
        srv = self._srv()
        result, offset = srv._psbt_parse_map(bytes([0x00, 0x00, 0x00]), 0)
        assert result == {}
        assert offset == 1
