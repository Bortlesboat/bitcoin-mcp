"""Tests for PSBT security analysis tools (analyze_psbt_security, explain_inscription_listing_security).

The analyze_psbt_security tool analyzes BIP 174 PSBTs for ordinals inscription listing
vulnerabilities — specifically SIGHASH_SINGLE|ANYONECANPAY without 2-of-2 multisig.

The _psbt_analyze function is a pure PSBT parser that returns error dicts for invalid input.
The tool wrappers (analyze_psbt_security, explain_inscription_listing_security) call it and
return JSON or string respectively.
"""

import json
import pytest


class TestPSBTSecurityAnalysis:
    """Tests for _psbt_analyze and its public tool wrappers."""

    @staticmethod
    def _srv():
        """Import server module."""
        import bitcoin_mcp.server as srv
        return srv

    # === Error path tests (reliable) ===

    def test_invalid_hex_returns_error_dict(self):
        """Garbage hex string returns {'error': '...'} instead of raising."""
        srv = self._srv()
        result = srv._psbt_analyze('ZZZZ')
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Invalid hex encoding' in result['error']

    def test_empty_hex_returns_error(self):
        """Empty string returns error dict."""
        srv = self._srv()
        result = srv._psbt_analyze('')
        assert isinstance(result, dict)
        assert 'error' in result

    def test_raw_bitcoin_tx_not_psbt(self):
        """Raw Bitcoin transaction hex is not a PSBT — wrong magic bytes."""
        srv = self._srv()
        # Raw Bitcoin tx: version=2, 1 input, 1 output
        raw_tx = '0200000001abcdef00000000000000000000000000ffffffff01e8030000000000001976a914d85c2b71d0060b09c8816b7b1f1c9aab79d9b7fe88ac00000000'
        result = srv._psbt_analyze(raw_tx)
        assert 'error' in result
        assert 'magic' in result['error'].lower()

    def test_wrong_magic_rejected(self):
        """PSBT with non-psbt magic bytes is rejected."""
        srv = self._srv()
        # 10 bytes of zeros as "PSBT"
        result = srv._psbt_analyze('00000000000000000000000000')
        assert 'error' in result

    def test_magic_only_is_error(self):
        """PSBT with only magic bytes (no global map) is rejected."""
        srv = self._srv()
        result = srv._psbt_analyze('70736274ff')
        assert 'error' in result

    # === Tool wrapper tests ===

    def test_analyze_psbt_security_returns_string(self):
        """analyze_psbt_security returns a JSON string for error inputs."""
        srv = self._srv()
        # For inputs that don't crash the internal parser with IndexError,
        # the wrapper returns a JSON string
        result = srv.analyze_psbt_security('ZZZZ')
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert 'error' in parsed

    def test_analyze_psbt_security_catches_invalid_hex(self):
        """analyze_psbt_security wraps hex errors in JSON."""
        srv = self._srv()
        result = srv.analyze_psbt_security('ZZZZ')
        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'Invalid hex encoding' in parsed['error']

    def test_explain_inscription_returns_error_string_for_invalid(self):
        """explain_inscription_listing_security returns error string for bad input."""
        srv = self._srv()
        result = srv.explain_inscription_listing_security('ZZZZ')
        assert isinstance(result, str)
        assert 'error' in result.lower() or 'Invalid' in result

    def test_explain_inscription_returns_error_for_invalid_input(self):
        """explain_inscription_listing_security returns error string for invalid input."""
        srv = self._srv()
        # Non-hex input triggers exception at binascii.unhexlify step
        result = srv.explain_inscription_listing_security('ZZZZ')
        assert isinstance(result, str)
        assert len(result) > 0

    def test_analyze_psbt_always_returns_str_not_dict(self):
        """Public tool analyze_psbt_security always returns str (JSON), never raw dict."""
        srv = self._srv()
        for bad_input in ['ZZZZ', '', '0000', '70736274ff']:
            result = srv.analyze_psbt_security(bad_input)
            assert isinstance(result, str), f"Expected str for {bad_input}, got {type(result)}"
            # Must be parseable as JSON
            json.loads(result)


class TestPSBTAnalysisInputValidation:
    """Tests verifying _psbt_analyze correctly validates PSBT structure."""

    @staticmethod
    def _srv():
        import bitcoin_mcp.server as srv
        return srv

    def test_psbt_magic_bytes_correct(self):
        """Verify _PSBT_MAGIC constant is correct BIP 174 magic."""
        srv = self._srv()
        assert srv._PSBT_MAGIC == b'psbt\xff'

    def test_sighash_names_defined(self):
        """Verify SIGHASH constant mapping exists."""
        srv = self._srv()
        assert srv._PSBT_SIGHASH_NAMES[0x01] == 'SIGHASH_ALL'
        assert srv._PSBT_SIGHASH_NAMES[0x83] == 'SIGHASH_SINGLE|ANYONECANPAY'
        assert srv._PSBT_SIGHASH_NAMES[0x81] == 'SIGHASH_ALL|ANYONECANPAY'

    def test_varint_read_roundtrip(self):
        """Verify _psbt_read_varint handles all varint sizes."""
        srv = self._srv()
        # Single byte (0x00 to 0xfc)
        val, off = srv._psbt_read_varint(bytes([0x00, 0x00, 0x00]), 0)
        assert val == 0 and off == 1
        val, off = srv._psbt_read_varint(bytes([0xfc, 0x00, 0x00]), 0)
        assert val == 0xfc and off == 1
        # Two byte (0xfd + 2 bytes LE)
        val, off = srv._psbt_read_varint(bytes([0xfd, 0x01, 0x00, 0x00]), 0)
        assert val == 1 and off == 3
        # Four byte (0xfe + 4 bytes LE)
        val, off = srv._psbt_read_varint(bytes([0xfe, 0x01, 0x00, 0x00, 0x00, 0x00]), 0)
        assert val == 1 and off == 5
        # Eight byte (0xff + 8 bytes LE)
        val, off = srv._psbt_read_varint(bytes([0xff, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), 0)
        assert val == 1 and off == 9

    def test_is_2of2_multisig_true(self):
        """_psbt_is_2of2_multisig returns True for valid 2-of-2 P2WSH script."""
        srv = self._srv()
        # OP_2 <33-byte-pubkey1> <33-byte-pubkey2> OP_2 OP_CHECKMULTISIG
        # Hex: 52 | 21 | [33 bytes of 0x11] | 21 | [33 bytes of 0x22] | 52 | AE
        # '11' * 33 = 33 repetitions of hex byte 0x11 = 33 bytes
        # '22' * 33 = 33 repetitions of hex byte 0x22 = 33 bytes
        valid_script = bytes.fromhex('5221' + '11' * 33 + '21' + '22' * 33 + '52ae')
        assert len(valid_script) == 71, f"Expected 71 bytes, got {len(valid_script)}"
        assert srv._psbt_is_2of2_multisig(valid_script) is True

    def test_is_2of2_multisig_false_wrong_length(self):
        """_psbt_is_2of2_multisig returns False for wrong-length scripts."""
        srv = self._srv()
        # Wrong length (70 bytes instead of 71)
        short_script = bytes.fromhex('5221' + '11' * 65 + '21' + '22' * 66 + '52ae')
        assert srv._psbt_is_2of2_multisig(short_script) is False
        # Wrong length (72 bytes)
        long_script = bytes.fromhex('5221' + '11' * 66 + '21' + '22' * 66 + '52ae00')
        assert srv._psbt_is_2of2_multisig(long_script) is False

    def test_is_2of2_multisig_false_non_multisig(self):
        """_psbt_is_2of2_multisig returns False for non-multisig scripts."""
        srv = self._srv()
        # Regular P2PKH script
        p2pkh = bytes.fromhex('76a914d85c2b71d0060b09c8816b7b1f1c9aab79d9b7fe88ac')
        assert srv._psbt_is_2of2_multisig(p2pkh) is False

    def test_psbt_parse_map_empty(self):
        """_psbt_parse_map returns empty dict at separator (key_len=0)."""
        srv = self._srv()
        # Start with 0x00 (key_len=0 separator)
        result, offset = srv._psbt_parse_map(bytes([0x00, 0x00, 0x00]), 0)
        assert result == {}
        assert offset == 1
