from ulid import ULID


def generate_ulid() -> str:
    """Generate a new ULID string (26 characters)."""
    return str(ULID())
