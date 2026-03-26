"""L402 client for paying Satoshi API endpoints with Lightning.

Handles the full L402 flow:
1. Request endpoint → get 402 with macaroon + invoice
2. Pay invoice (mock or real Lightning)
3. Retry with L402 Authorization header
4. Cache valid tokens for reuse
"""

import base64
import hashlib
import json
import logging
import os
import time

log = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class L402Client:
    """HTTP client with automatic L402 Lightning payment handling."""

    def __init__(self, base_url: str, auto_pay: bool = True, max_sats_per_request: int = 1000):
        if not HAS_HTTPX:
            raise ImportError("httpx is required for L402 client. Install with: pip install bitcoin-mcp[l402]")
        from bitcoin_mcp import __version__
        self.base_url = base_url.rstrip("/")
        self.auto_pay = auto_pay
        self.max_sats_per_request = max_sats_per_request
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=30.0,
            headers={"User-Agent": f"bitcoin-mcp/{__version__}"},
        )
        self._token_cache: dict[str, tuple[str, float]] = {}  # endpoint -> (auth_header, expiry)

    def get(self, path: str, params: dict | None = None) -> dict:
        """GET a Satoshi API endpoint, auto-paying via L402 if needed."""
        # Check cache for valid token
        cached = self._token_cache.get(path)
        if cached:
            auth_header, expiry = cached
            if time.time() < expiry:
                resp = self.client.get(path, params=params, headers={"Authorization": auth_header})
                if resp.status_code == 200:
                    return resp.json()
                # Token expired or invalid, clear cache
                del self._token_cache[path]

        # First attempt without L402
        resp = self.client.get(path, params=params)
        if resp.status_code != 402:
            resp.raise_for_status()
            return resp.json()

        if not self.auto_pay:
            raise L402PaymentRequired(resp)

        # Parse 402 challenge
        www_auth = resp.headers.get("WWW-Authenticate", "")
        price_sats = int(resp.headers.get("X-Price-Sats", "0"))

        if price_sats > self.max_sats_per_request:
            raise L402PriceTooHigh(price_sats, self.max_sats_per_request)

        macaroon_b64, invoice = _parse_l402_challenge(www_auth)
        if not macaroon_b64 or not invoice:
            raise L402ProtocolError("Could not parse L402 challenge from WWW-Authenticate header")

        # Pay the invoice (mock: generate preimage from payment hash in macaroon)
        preimage_hex = self._pay_invoice(invoice, macaroon_b64)

        # Retry with L402 auth
        auth_header = f"L402 {macaroon_b64}:{preimage_hex}"
        resp = self.client.get(path, params=params, headers={"Authorization": auth_header})
        resp.raise_for_status()

        # Cache the token (assume 1 hour validity)
        self._token_cache[path] = (auth_header, time.time() + 3500)

        log.info("L402: Paid %d sats for %s", price_sats, path)
        return resp.json()

    def _pay_invoice(self, invoice: str, macaroon_b64: str) -> str:
        """Pay a Lightning invoice. Override for real Lightning integration."""
        # For mock/testing: derive preimage from the macaroon's payment_hash
        # In production, this would call a Lightning node to pay the invoice
        try:
            mac_json = json.loads(base64.urlsafe_b64decode(macaroon_b64))
            ident = json.loads(mac_json["identifier"])
            payment_hash = ident["payment_hash"]
            # Mock: preimage is just the payment_hash reversed (for testing only)
            # Real implementation would get preimage from Lightning payment
            log.warning("L402: Using mock payment — override _pay_invoice for real Lightning")
            return payment_hash  # This won't verify in production
        except Exception as e:
            raise L402ProtocolError(f"Failed to extract payment hash: {e}")

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "L402Client":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class L402PaymentRequired(Exception):
    def __init__(self, response: object) -> None:
        self.response = response
        super().__init__(f"Payment required: {response.status_code}")


class L402PriceTooHigh(Exception):
    def __init__(self, price: int, max_price: int) -> None:
        self.price = price
        self.max_price = max_price
        super().__init__(f"Price {price} sats exceeds max {max_price} sats")


class L402ProtocolError(Exception):
    pass


def _parse_l402_challenge(www_auth: str) -> tuple[str | None, str | None]:
    """Parse WWW-Authenticate: L402 macaroon="...", invoice="..." """
    if not www_auth.startswith("L402 "):
        return None, None
    macaroon_b64 = None
    invoice = None
    for part in www_auth[5:].split(","):
        part = part.strip()
        if part.startswith('macaroon="') and part.endswith('"'):
            macaroon_b64 = part[10:-1]
        elif part.startswith('invoice="') and part.endswith('"'):
            invoice = part[9:-1]
    return macaroon_b64, invoice
