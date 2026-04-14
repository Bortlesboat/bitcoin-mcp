"""Tests for the L402 Lightning payment client."""

import time
from unittest.mock import MagicMock, patch

import pytest

from bitcoin_mcp.l402_client import (
    L402Client,
    L402PaymentRequired,
    L402PriceTooHigh,
    _parse_l402_challenge,
)


def test_parse_l402_challenge_happy_path():
    macaroon, invoice = _parse_l402_challenge(
        'L402 macaroon="FM_1HRv7...", invoice="lnbc1..."'
    )
    assert macaroon == "FM_1HRv7..."
    assert invoice == "lnbc1..."


def test_parse_l402_challenge_with_spaces():
    macaroon, invoice = _parse_l402_challenge(
        'L402 macaroon="mac123", invoice="lnbc2..."'
    )
    assert macaroon == "mac123"
    assert invoice == "lnbc2..."


def test_parse_l402_challenge_malformed_missing_macaroon():
    macaroon, invoice = _parse_l402_challenge('L402 invoice="lnbc1..."')
    assert macaroon is None
    assert invoice == "lnbc1..."


def test_parse_l402_challenge_malformed_missing_invoice():
    macaroon, invoice = _parse_l402_challenge('L402 macaroon="mac123"')
    assert macaroon == "mac123"
    assert invoice is None


def test_parse_l402_challenge_malformed_wrong_scheme():
    macaroon, invoice = _parse_l402_challenge("Bearer abc123")
    assert macaroon is None
    assert invoice is None


def test_parse_l402_challenge_empty_string():
    macaroon, invoice = _parse_l402_challenge("")
    assert macaroon is None
    assert invoice is None


def test_l402_price_too_high_exception():
    exc = L402PriceTooHigh(price=5000, max_price=1000)
    assert exc.price == 5000
    assert exc.max_price == 1000
    assert "5000 sats exceeds max 1000 sats" in str(exc)


@patch("httpx.Client")
def test_get_raises_l402_price_too_high(mock_httpx_client_cls):
    mock_client_instance = MagicMock()
    mock_httpx_client_cls.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.status_code = 402
    mock_response.headers = {
        "WWW-Authenticate": 'L402 macaroon="mac123", invoice="lnbc1..."',
        "X-Price-Sats": "500",
    }
    mock_client_instance.get.return_value = mock_response

    client = L402Client("https://api.example.com", auto_pay=True, max_sats_per_request=100)

    with pytest.raises(L402PriceTooHigh) as exc_info:
        client.get("/some_endpoint")

    assert exc_info.value.price == 500
    assert exc_info.value.max_price == 100


@patch("httpx.Client")
def test_get_raises_l402_payment_required_when_auto_pay_false(mock_httpx_client_cls):
    mock_client_instance = MagicMock()
    mock_httpx_client_cls.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.status_code = 402
    mock_response.headers = {
        "WWW-Authenticate": 'L402 macaroon="mac123", invoice="lnbc1..."',
        "X-Price-Sats": "50",
    }
    mock_client_instance.get.return_value = mock_response

    client = L402Client("https://api.example.com", auto_pay=False, max_sats_per_request=10000)

    with pytest.raises(L402PaymentRequired) as exc_info:
        client.get("/some_endpoint")

    assert exc_info.value.response.status_code == 402


@patch("httpx.Client")
def test_token_cache_reuses_valid_token(mock_httpx_client_cls):
    mock_client_instance = MagicMock()
    mock_httpx_client_cls.return_value = mock_client_instance

    mock_ok_response = MagicMock()
    mock_ok_response.status_code = 200
    mock_ok_response.json.return_value = {"result": "ok"}
    mock_client_instance.get.return_value = mock_ok_response

    client = L402Client("https://api.example.com")
    client._token_cache["/endpoint"] = ("L402 mac123:preimage456", time.time() + 3600)

    result = client.get("/endpoint")

    assert result == {"result": "ok"}
    call_args = mock_client_instance.get.call_args
    assert call_args[1]["headers"]["Authorization"] == "L402 mac123:preimage456"


@patch("httpx.Client")
@patch.object(L402Client, "_pay_invoice", return_value="fake_preimage_123")
def test_token_cache_expired_cleared_and_retried(mock_pay_invoice, mock_httpx_client_cls):
    mock_client_instance = MagicMock()
    mock_httpx_client_cls.return_value = mock_client_instance

    mock_402 = MagicMock()
    mock_402.status_code = 402
    mock_402.headers = {
        "WWW-Authenticate": 'L402 macaroon="bmV3X21hYw==", invoice="lnbc1..."',
        "X-Price-Sats": "10",
    }

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {"paid": True}

    mock_client_instance.get.side_effect = [mock_402, mock_200]

    client = L402Client("https://api.example.com", auto_pay=True, max_sats_per_request=10000)
    client._token_cache["/endpoint"] = ("L402 old_mac:old_pre", time.time() - 10)

    result = client.get("/endpoint")

    assert result == {"paid": True}
    assert "/endpoint" in client._token_cache


def test_l402_client_requires_httpx():
    with patch("bitcoin_mcp.l402_client.HAS_HTTPX", False):
        with pytest.raises(ImportError, match="httpx"):
            L402Client("https://api.example.com")
