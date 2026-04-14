"""Tests for lightweight Bitcoin address validation."""

import json

import pytest


def test_validate_address_format_rejects_empty_string():
    from bitcoin_mcp.address_validation import _validate_address_format

    assert _validate_address_format("") == "Address cannot be empty."


def test_validate_address_format_rejects_too_short_address():
    from bitcoin_mcp.address_validation import _validate_address_format

    result = _validate_address_format("1A1zP1eP5")
    assert "Invalid address length" in result


def test_validate_address_format_rejects_bad_prefix():
    from bitcoin_mcp.address_validation import _validate_address_format

    result = _validate_address_format("https://example.com/not-a-bitcoin-address")
    assert "Unrecognized address format" in result


def test_validate_address_format_accepts_valid_address():
    from bitcoin_mcp.address_validation import _validate_address_format

    assert _validate_address_format("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") is None


@pytest.mark.parametrize(
    ("tool_name", "kwargs"),
    [
        ("get_address_utxos", {}),
        ("validate_address", {}),
        ("get_address_balance", {}),
        ("get_address_history", {"offset": 0, "limit": 25}),
    ],
)
def test_address_tools_reject_obviously_invalid_input(tool_name, kwargs):
    import bitcoin_mcp.server as server

    tool = getattr(server, tool_name)
    result = json.loads(tool("not-a-bitcoin-address", **kwargs))

    assert "error" in result
    assert "Invalid address" in result["error"]
