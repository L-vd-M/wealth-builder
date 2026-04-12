"""Symmetric encryption for sensitive values (API keys) stored in the database.

Requires the ENCRYPTION_KEY environment variable — a URL-safe base64-encoded
32-byte Fernet key.  Generate one with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import os

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY environment variable is not set")
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    """Return a URL-safe base64 ciphertext string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Return the original plaintext.  Raises ValueError on tampered/wrong-key data."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt value — wrong key or tampered data") from exc
