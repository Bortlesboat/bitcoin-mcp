#!/usr/bin/env python3
"""Generate valid test extended keys for decode_xpub tests."""

import hashlib
import hmac
import struct
import base58

# secp256k1
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

def point_mul(k):
    rx, ry = 0, 0
    px, py = GX, GY
    while k > 0:
        if k & 1:
            if rx == 0:
                rx, ry = px, py
            else:
                lam = ((py - ry) * pow(px - rx, -1, P)) % P
                rx = (lam * lam - px - rx) % P
                ry = (lam * (px - rx) - py) % P
        lam = ((3 * px * px) * pow(2 * py, -1, P)) % P
        qx = (lam * lam - 2 * px) % P
        qy = (lam * (px - qx) - py) % P
        px, py = qx, qy
        k >>= 1
    return (rx % P, ry % P)

def make_extkey(version_hex, chaincode, pubkey):
    version = bytes.fromhex(version_hex)
    ext = version + bytes([0]) + b'\x00\x00\x00\x00' + struct.pack('>I', 0) + chaincode + pubkey
    checksum = hashlib.sha256(hashlib.sha256(ext).digest()).digest()[:4]
    return base58.b58encode(ext + checksum).decode()

seed = b'test seed for bitcoin mcp decode_xpub tests 123456'
h = hmac.new(b'Bitcoin seed', seed, hashlib.sha512).digest()
priv_key, chaincode = h[:32], h[32:]

pubx, puby = point_mul(int.from_bytes(priv_key, 'big'))
prefix = bytes([0x02 if puby % 2 == 0 else 0x03])
pubkey = prefix + pubx.to_bytes(32, 'big')

# xpub
print(f'    TEST_XPUB = "{make_extkey("0488b21e", chaincode, pubkey)}"')
# tpub
print(f'    TEST_TPUB = "{make_extkey("043587cf", chaincode, pubkey)}"')
# ypub
print(f'    TEST_YPUB = "{make_extkey("049d7b2e", chaincode, pubkey)}"')
# zpub
print(f'    TEST_ZPUB = "{make_extkey("04b24746", chaincode, pubkey)}"')
# xprv
ext_xprv = bytes.fromhex("0488ade4") + bytes([0]) + b'\x00\x00\x00\x00' + struct.pack('>I', 0) + chaincode + b'\x00'*33
checksum = hashlib.sha256(hashlib.sha256(ext_xprv).digest()).digest()[:4]
print(f'    TEST_XPRV = "{base58.b58encode(ext_xprv + checksum).decode()}"')
