"""
Reset the password for an existing admin user.

Reads all values from environment variables — no hardcoded credentials.

Usage (Windows):
  set DATABASE_URL=postgresql://user:pass@host:port/wasl_prod
  set ADMIN_EMAIL=admin@yourcompany.eg
  set NEW_ADMIN_PASSWORD=NewStrongPassword1!
  python scripts/reset_admin_password.py

Usage (macOS / Linux):
  export DATABASE_URL=postgresql://user:pass@host:port/wasl_prod
  export ADMIN_EMAIL=admin@yourcompany.eg
  export NEW_ADMIN_PASSWORD=NewStrongPassword1!
  python scripts/reset_admin_password.py

What the script does:
  1. Validates the new password meets complexity requirements.
  2. Hashes it with the same bcrypt function used at registration.
  3. Writes the new hash to the database.
  4. Clears the in-memory failed-attempt / lockout counter for that email.
  5. Revokes all existing refresh-token sessions (sets revoked_at = now).

The script is idempotent — safe to run again with the same password.
"""

import os
import sys
from datetime import datetime, timezone

# Ensure backend modules are importable when run from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal  # noqa: E402
from models.user import User  # noqa: E402
from models.user_session import UserSession  # noqa: E402
from security.password import (  # noqa: E402
    hash_password,
    validate_password_complexity,
)


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL")
    new_password = os.environ.get("NEW_ADMIN_PASSWORD")

    if not email or not new_password:
        print("ERROR: Both ADMIN_EMAIL and NEW_ADMIN_PASSWORD must be set.")
        print()
        print("  set ADMIN_EMAIL=admin@yourcompany.eg")
        print("  set NEW_ADMIN_PASSWORD=NewStrongPassword1!")
        sys.exit(1)

    # Validate password complexity before touching the database
    errors = validate_password_complexity(new_password)
    if errors:
        print("ERROR: New password does not meet complexity requirements:")
        for msg in errors:
            print(f"  - {msg}")
        sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        if user is None:
            print(f"ERROR: No user found with email '{email}'.")
            sys.exit(1)

        if user.role != "admin":
            print(
                f"ERROR: User '{email}' has role '{user.role}', not 'admin'. "
                "Refusing to reset."
            )
            sys.exit(1)

        # 1. Update password hash
        user.password_hash = hash_password(new_password)

        # 2. Revoke all existing refresh-token sessions
        now = datetime.now(timezone.utc)
        sessions = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
            .all()
        )
        for session in sessions:
            session.revoked_at = now
        revoked_count = len(sessions)

        db.commit()

        # 3. Clear the in-memory failed-attempt / lockout counter.
        #    Import after sys.path manipulation so the backend env vars
        #    are already set when auth_service is first imported.
        from services.auth_service import _clear_lockout  # noqa: E402
        _clear_lockout(email)

        print(f"Password reset successfully for: {email}")
        print(f"Sessions revoked: {revoked_count}")
        print("Lockout counter cleared.")
        print("The user can now log in with the new password.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
