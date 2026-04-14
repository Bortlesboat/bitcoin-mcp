"""Fast, lightweight Bitcoin address validation helpers."""

MIN_ADDRESS_LENGTH = 25
MAX_ADDRESS_LENGTH = 90
VALID_ADDRESS_PREFIXES = (
    "1",
    "3",
    "bc1q",
    "bc1p",
    "tb1q",
    "tb1p",
    "m",
    "n",
    "2",
    "bcrt1",
)


def _validate_address_format(address: str) -> str | None:
    """Return an error message if the address is obviously invalid, else None."""
    if not address or not address.strip():
        return "Address cannot be empty."

    address = address.strip()

    if len(address) < MIN_ADDRESS_LENGTH or len(address) > MAX_ADDRESS_LENGTH:
        return (
            f"Invalid address length ({len(address)}). "
            f"Bitcoin addresses are {MIN_ADDRESS_LENGTH}-{MAX_ADDRESS_LENGTH} characters."
        )

    if not any(address.startswith(prefix) for prefix in VALID_ADDRESS_PREFIXES):
        return (
            "Unrecognized address format. Expected prefix: "
            + ", ".join(VALID_ADDRESS_PREFIXES)
        )

    return None
