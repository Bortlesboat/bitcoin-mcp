"""Tests for Bitcoin address validation."""

import pytest


class TestValidateAddressFormat:
    """Tests for the _validate_address_format helper."""

    def test_empty_string_returns_error(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("")
        assert result is not None
        assert "cannot be empty" in result

    def test_whitespace_only_returns_error(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("   ")
        assert result is not None
        assert "cannot be empty" in result

    def test_none_returns_error(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format(None)
        assert result is not None
        assert "cannot be empty" in result

    def test_too_short_address_returns_error(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("1A1zP1eP5")
        assert result is not None
        assert "Invalid address length" in result
        assert "9" in result  # the length should be mentioned

    def test_too_long_address_returns_error(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        long_addr = "1" * 100
        result = _validate_address_format(long_addr)
        assert result is not None
        assert "Invalid address length" in result
        assert "100" in result

    def test_bad_prefix_returns_error(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("https://example.com/not-an-address")
        assert result is not None
        assert "Unrecognized address format" in result

    def test_valid_legacy_address_passes(self):
        """Genesis block address."""
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert result is None

    def test_valid_p2sh_address_passes(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy")
        assert result is None

    def test_valid_bech32_address_passes(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
        assert result is None

    def test_valid_taproot_address_passes(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge8ztwac72sfr9rusxg3297")
        assert result is None

    def test_valid_testnet_bech32_passes(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx")
        assert result is None

    def test_valid_testnet_p2pkh_passes(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("mipcBbFg9gMiCh81Kj8tqqdgoZub1ZJRfn")
        assert result is None

    def test_leading_trailing_whitespace_strips_and_validates(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("  1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa  ")
        assert result is None

    def test_valid_regtest_address_passes(self):
        from bitcoin_mcp.address_validation import _validate_address_format

        result = _validate_address_format("bcrt1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
        assert result is None

