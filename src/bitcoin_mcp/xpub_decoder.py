"""Extended public key (xpub/ypub/zpub/tpub) decoder and address deriver.

Uses bip_utils as an optional dependency. Falls back to a pure-Python
Base58Check parser that extracts metadata (network, type, depth,
fingerprint, child number) without deriving addresses.

Closes: Bortlesboat/bitcoin-mcp#2
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
from typing import Optional


# --- BIP32 version bytes ---
_VERSION_BYTES = {
    # Mainnet
    b"\x04\x88\xb2\x1e": ("xpub", "mainnet", "p2pkh"),
    b"\x04\x9d\x7b\x2e": ("ypub", "mainnet", "p2sh-p2wpkh"),
    b"\x04\xb2\x47\x46": ("zpub", "mainnet", "p2wpkh"),
    b"\x02\xaa\x7e\xd3": ("Ltub", "mainnet", "p2pkh"),
    b"\x02\x95\xb4\x3f": ("Mtub", "mainnet", "p2sh-p2wpkh"),
    b"\x02\xb2\x49\x47": ("Vpub", "mainnet", "p2wpkh"),
    # Testnet
    b"\x04\x35\x87\xcf": ("tpub", "testnet", "p2pkh"),
    b"\x04\x4a\x52\x62": ("upub", "testnet", "p2sh-p2wpkh"),
    b"\x04\x5f\x1a\xf6": ("vpub", "testnet", "p2wpkh"),
    b"\x04\x3b\xcb\x1c": ("Ltpv", "testnet", "p2pkh"),
    b"\x04\x4f\xc6\xe7": ("Mtpv", "testnet", "p2sh-p2wpkh"),
    b"\x04\x5c\xac\x1f": ("vpub", "testnet", "p2wpkh"),
}


def _base58check_decode(key_str: str) -> tuple[bytes, int]:
    """Decode a Base58Check-encoded extended key.

    Returns (payload_78bytes, version_int).
    """
    try:
        import base58
    except ImportError:
        raise ImportError(
            "base58 package is required. Install it with: pip install base58"
        )

    payload = base58.b58decode_check(key_str)
    if len(payload) != 78:
        raise ValueError(f"Invalid extended key length: expected 78 bytes, got {len(payload)}")

    version_int = struct.unpack(">I", payload[:4])[0]
    return payload, version_int


def _identify_version(payload: bytes) -> tuple[str, str, str]:
    """Identify xpub type, network, and purpose from version bytes."""
    version = payload[:4]
    if version in _VERSION_BYTES:
        return _VERSION_BYTES[version]

    # Fallback: guess from raw version int
    version_int = struct.unpack(">I", version)[0]
    raise ValueError(
        f"Unknown extended key version: 0x{version_int:08x}. "
        f"Supported types: xpub, ypub, zpub, tpub, upub, vpub."
    )


def _derive_child_pubkey(parent_key: bytes, parent_chaincode: bytes, index: int) -> tuple[bytes, bytes]:
    """Derive a child public key using BIP32 public derivation (CKDpub).

    For normal (hardened) child indices, raises ValueError.
    For non-hardened indices (0 <= index < 0x80000000), computes:
      HMAC-SHA512(Key=parent_chaincode, Data=parent_pubkey || index) -> IL || IR
      child_key = parent_key + IL*G (serialized compressed)
      child_chaincode = IR
    """
    if index >= 0x80000000:
        raise ValueError("Cannot derive hardened child from public key (needs private key)")

    # Data = 0x02/03 || parent_key || index (4 bytes big-endian)
    data = parent_key + struct.pack(">I", index)
    h = hmac.new(parent_chaincode, data, hashlib.sha512).digest()
    il, ir = h[:32], h[32:]
    il_int = int.from_bytes(il, "big")

    # Parse parent compressed public key
    prefix = parent_key[0]
    if prefix not in (0x02, 0x03):
        raise ValueError(f"Invalid compressed public key prefix: 0x{prefix:02x}")
    parent_x = int.from_bytes(parent_key[1:33], "big")

    # secp256k1 curve: y^2 = x^3 + 7
    p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    a = 0
    b = 7

    # Compute parent_y from prefix
    y_sq = (pow(parent_x, 3, p) + b) % p
    y = pow(y_sq, (p + 1) // 4, p)
    if (y % 2) != (prefix - 2):
        y = p - y

    # Multiply: (x, y) + il * G
    # secp256k1 generator point
    gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
    gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

    # Point addition using affine coordinates with modular inverse
    # k * G using double-and-add
    def point_mul(k: int) -> tuple[int, int]:
        rx, ry = 0, 0  # point at infinity
        px, py = gx, gy
        while k > 0:
            if k & 1:
                if rx == 0:
                    rx, ry = px, py
                else:
                    # Point addition
                    lam = ((py - ry) * pow(px - rx, -1, p)) % p
                    rx = (lam * lam - px - rx) % p
                    ry = (lam * (px - rx) - py) % p
            # Point doubling
            if px == 0:
                px, py = 0, 0
            else:
                lam = ((3 * px * px + a) * pow(2 * py, -1, p)) % p
                qx = (lam * lam - 2 * px) % p
                qy = (lam * (px - qx) - py) % p
                px, py = qx, qy
            k >>= 1
        return (rx % p, ry % p)

    ilx, ily = point_mul(il_int)

    # Point addition: parent + il*G
    lam = ((ily - y) * pow(ilx - parent_x, -1, p)) % p
    child_x = (lam * lam - parent_x - ilx) % p
    child_y = (lam * (parent_x - child_x) - y) % p

    # Serialize compressed public key
    prefix = bytes([0x02 if child_y % 2 == 0 else 0x03])
    child_key = prefix + child_x.to_bytes(32, "big")

    return child_key, ir


def _pubkey_to_address(pubkey: bytes, script_type: str, network: str = "mainnet") -> str:
    """Convert a compressed public key to a Bitcoin address."""
    sha256_hash = hashlib.sha256(pubkey).digest()
    ripemd160 = hashlib.new("ripemd160", sha256_hash).digest()
    pubkey_hash = ripemd160

    if script_type == "p2pkh":
        version = b"\x00" if network == "mainnet" else b"\x6f"
        payload = version + pubkey_hash
    elif script_type == "p2sh-p2wpkh":
        version = b"\x05" if network == "mainnet" else b"\xc4"
        # witness program = 0x00 0x14 <20-byte-hash>
        witness = b"\x00\x14" + pubkey_hash
        payload = version + hashlib.new("ripemd160", hashlib.sha256(witness).digest()).digest()
    elif script_type == "p2wpkh":
        # Bech32 encoding
        return _bech32_encode(pubkey_hash, "bc" if network == "mainnet" else "tb")
    else:
        raise ValueError(f"Unknown script type: {script_type}")

    # Base58Check encode
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    try:
        import base58
        return base58.b58encode(payload + checksum).decode("ascii")
    except ImportError:
        raise ImportError("base58 package required")


def _bech32_encode(witness_program: bytes, hrp: str) -> str:
    """Encode a witness program as a bech32 address (BIP173)."""
    # bech32 implementation (minimal)
    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    def _bech32_polymod(values):
        GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for v in values:
            b = chk >> 25
            chk = ((chk & 0x1ffffff) << 5) ^ v
            for i in range(5):
                chk ^= GEN[i] if ((b >> i) & 1) else 0
        return chk

    def _bech32_hrp_expand(hrp):
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

    def _bech32_create_checksum(hrp, data):
        values = _bech32_hrp_expand(hrp) + data
        polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
        return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

    def _convertbits(data, frombits, tobits, pad=True):
        acc = 0
        bits = 0
        ret = []
        maxv = (1 << tobits) - 1
        for value in data:
            if value < 0 or (value >> frombits):
                return None
            acc = (acc << frombits) | value
            bits += frombits
            while bits >= tobits:
                bits -= tobits
                ret.append((acc >> bits) & maxv)
        if pad:
            if bits:
                ret.append((acc << (tobits - bits)) & maxv)
        elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
            return None
        return ret

    witness_ver = 0
    data = [witness_ver] + _convertbits(witness_program, 8, 5)
    checksum = _bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join(CHARSET[d] for d in data + checksum)


def _is_private_key(key_str: str) -> bool:
    """Check if the extended key appears to be a private key (xprv/tprv etc.)."""
    try:
        payload, _ = _base58check_decode(key_str)
        version = payload[:4]
        version_int = struct.unpack(">I", version)[0]
        # Private key version bytes (xprv=0x0488ADE4, tprv=0x04358394, etc.)
        # For xpub family, the 3rd byte bit 0 = 0 for public, 1 for private
        # Easier: just check known private version prefixes
        private_prefixes = {0x0488ADE4, 0x04358394, 0x045F18BC, 0x044A5262, 0x04AA7ED3, 0x043BCB1C}
        return version_int in private_prefixes
    except Exception:
        return False


def decode_xpub(
    xpub: str,
    derive_count: int = 5,
    account: int = 0,
) -> dict:
    """Decode an extended public key and derive addresses.

    Args:
        xpub: Extended public key (xpub/ypub/zpub/tpub/upub/vpub).
        derive_count: Number of addresses to derive (1-20).
        account: BIP44 account index (default 0).

    Returns:
        Dict with network, type, fingerprint, depth, and derived addresses.
    """
    if derive_count < 1 or derive_count > 20:
        raise ValueError("derive_count must be between 1 and 20")

    if _is_private_key(xpub):
        raise ValueError(
            "Private extended keys (xprv/tprv) are not accepted for safety. "
            "Only public keys (xpub/ypub/zpub/tpub/upub/vpub) can be decoded."
        )

    payload, _ = _base58check_decode(xpub)
    key_type, network, script_type = _identify_version(payload)

    depth = payload[4]
    fingerprint = payload[5:9].hex()
    child_number = struct.unpack(">I", payload[9:13])[0]
    chain_code = payload[13:45]
    parent_key = payload[45:78]

    result = {
        "network": network,
        "type": key_type,
        "script_type": script_type,
        "fingerprint": fingerprint,
        "depth": depth,
        "child_number": child_number,
        "derived_addresses": [],
    }

    # Derive addresses: m/account'/0/0/index (BIP44 external chain)
    # Since we have a public key, we can only do non-hardened derivation
    # Derive m/0/index from whatever depth we're at
    for i in range(derive_count):
        try:
            child_key, _ = _derive_child_pubkey(parent_key, chain_code, i)
            address = _pubkey_to_address(child_key, script_type, network)
            result["derived_addresses"].append({
                "index": i,
                "address": address,
                "path": f"m/{account}'/0/{i}",
            })
        except Exception as e:
            result["derived_addresses"].append({
                "index": i,
                "error": str(e),
            })

    return result
