"""
User creation and lookup service.

All password operations go through security.password — never raw bcrypt here.
"""

from sqlalchemy.orm import Session

from models.user import User
from security.password import hash_password, validate_password_complexity
from schemas.auth_schema import RegisterRequest


class RegistrationError(Exception):
    """Raised when registration fails for a known reason."""

    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def register_user(db: Session, req: RegisterRequest) -> User:
    """Create a new user record.

    Raises RegistrationError for:
    - Weak password
    - Duplicate email
    - Duplicate phone
    """
    # 1. Password complexity
    errors = validate_password_complexity(req.password)
    if errors:
        raise RegistrationError(
            code="VALIDATION_ERROR",
            message="; ".join(errors),
            http_status=400,
        )

    # 2. Uniqueness checks (explicit, friendly errors)
    if db.query(User).filter(User.email == req.email).first():
        raise RegistrationError(
            code="DUPLICATE_EMAIL",
            message="This email address is already registered",
            http_status=409,
        )
    if db.query(User).filter(User.phone == req.phone).first():
        raise RegistrationError(
            code="DUPLICATE_PHONE",
            message="This phone number is already registered",
            http_status=409,
        )

    # 3. Create user — password is hashed, plaintext is discarded
    user = User(
        email=req.email,
        phone=req.phone,
        password_hash=hash_password(req.password),
        role=req.role,
        status="pending",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
