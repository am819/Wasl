"""
Password hashing utilities.

Uses bcrypt with a minimum of 12 rounds (> SECURITY.md minimum of 10).
Plain-text passwords are never stored, logged, or returned.
"""

from passlib.context import CryptContext

_PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Common passwords rejected during registration
_COMMON_PASSWORDS = {
    "password", "Password1!", "Password1", "12345678",
    "Qwerty123!", "Abc12345!", "Welcome1!", "Admin123!",
}


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*.  Never call with empty string."""
    return _PWD_CONTEXT.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _PWD_CONTEXT.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Password complexity validation
# ---------------------------------------------------------------------------

def _has_uppercase(s: str) -> bool:
    return any(c.isupper() for c in s)


def _has_lowercase(s: str) -> bool:
    return any(c.islower() for c in s)


def _has_digit(s: str) -> bool:
    return any(c.isdigit() for c in s)


def _has_special(s: str) -> bool:
    specials = set("!@#$%^&*()_+-=[]{}|;':\",./<>?`~\\")
    return any(c in specials for c in s)


def validate_password_complexity(password: str) -> list[str]:
    """Return a list of violation messages.  Empty list means valid."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not _has_uppercase(password):
        errors.append("Password must include at least one uppercase letter")
    if not _has_lowercase(password):
        errors.append("Password must include at least one lowercase letter")
    if not _has_digit(password):
        errors.append("Password must include at least one digit")
    if not _has_special(password):
        errors.append("Password must include at least one special character")
    if password in _COMMON_PASSWORDS:
        errors.append("Password is too common")
    return errors
