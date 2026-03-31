"""Bitcoin address format validation helpers."""


# Known valid prefixes for Bitcoin addresses
# Mainnet: 1 (P2PKH), 3 (P2SH), bc1 (Bech32/Bech32m)
# Testnet: m/n (P2PKH), 2 (P2SH), tb1 (Bech32/Bech32m)
# Regtest: bcrt1 (Bech32/Bech32m)
VALID_ADDRESS_PREFIXES = (
    "1", "3", "bc1q", "bc1p",  # mainnet
    "tb1q", "tb1p", "m", "n", "2",  # testnet
    "bcrt1q", "bcrt1p",  # regtest
)

VALID_PREFIXES_LIST = ", ".join(f"`{p}`" for p in VALID_ADDRESS_PREFIXES)

MIN_ADDRESS_LENGTH = 25
MAX_ADDRESS_LENGTH = 90


def _validate_address_format(address: str) -> str | None:
    """Validate that a Bitcoin address format is at least plausible.

    This is a fast sanity check, not full cryptographic validation.
    It catches empty strings, obviously wrong lengths, and unknown prefixes.

    Args:
        address: The Bitcoin address string to validate.

    Returns:
        An error message string if the address is obviously invalid, or
        ``None`` if the address passes the basic format checks.

    Examples:
        >>> _validate_address_format("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        None
        >>> _validate_address_format("")
        'Address cannot be empty.'
        >>> _validate_address_format("too short")
        'Invalid address length (9). Bitcoin addresses are 25-90 characters.'
        >>> _validate_address_format("https://example.com")
        'Unrecognized address format. Valid prefixes are: ...'
    """
    if not address or not address.strip():
        return "Address cannot be empty."

    stripped = address.strip()

    if len(stripped) < MIN_ADDRESS_LENGTH:
        return (
            f"Invalid address length ({len(stripped)}). "
            f"Bitcoin addresses are {MIN_ADDRESS_LENGTH}-{MAX_ADDRESS_LENGTH} characters."
        )

    if len(stripped) > MAX_ADDRESS_LENGTH:
        return (
            f"Invalid address length ({len(stripped)}). "
            f"Bitcoin addresses are {MIN_ADDRESS_LENGTH}-{MAX_ADDRESS_LENGTH} characters."
        )

    if not any(stripped.startswith(prefix) for prefix in VALID_ADDRESS_PREFIXES):
        return (
            f"Unrecognized address format `{stripped[:20]}...`. "
            f"Valid prefixes are: {VALID_PREFIXES_LIST}."
        )

    return None
