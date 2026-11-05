"""
AES-256 (Fernet) field-level encryption for sensitive database columns.

Used for: drivers.national_id_number, merchants.tax_id

The key is read from the ENCRYPTION_KEY environment variable (a Fernet key).
In development the placeholder key is accepted; production raises on startup.

Never log, print, or return decrypted values unnecessarily.
"""

from cryptography.fernet import Fernet, InvalidToken

from config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.encryption_key
        # In development, if the placeholder is set, generate a one-time key
        # so the app can start without a real key (tests use a fixed test key).
        if key in {"CHANGE_ME_BEFORE_USE", "CHANGE_ME_IN_PRODUCTION_32_BYTE_FERNET_KEY"}:
            key = Fernet.generate_key().decode()
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_field(plaintext: str) -> str:
    """Return base64-encoded Fernet ciphertext for *plaintext*."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    """Return decrypted plaintext from *ciphertext*.

    Raises cryptography.fernet.InvalidToken if the ciphertext is corrupt
    or was encrypted with a different key.
    """
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def reset_fernet_for_test() -> None:
    """Force re-initialisation of the Fernet instance. Test-only."""
    global _fernet
    _fernet = None
