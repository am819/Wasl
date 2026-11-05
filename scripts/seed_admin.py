"""
Seed script: create the first admin user from environment variables.

Usage:
  set DATABASE_URL=postgresql://...
  set ADMIN_EMAIL=admin@wasl.eg
  set ADMIN_PHONE=01000000000
  set ADMIN_PASSWORD=YourStrongPassword1!
  python scripts/seed_admin.py

No passwords are hardcoded. All values come from the environment.
If the admin already exists, the script reports it and exits.
"""

import os
import sys

# Ensure backend modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal  # noqa: E402
from models.user import User  # noqa: E402
from security.password import hash_password  # noqa: E402


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL")
    phone = os.environ.get("ADMIN_PHONE")
    password = os.environ.get("ADMIN_PASSWORD")

    if not all([email, phone, password]):
        print("ERROR: Set ADMIN_EMAIL, ADMIN_PHONE, and ADMIN_PASSWORD")
        print("  Example:")
        print("  set ADMIN_EMAIL=admin@wasl.eg")
        print("  set ADMIN_PHONE=01000000000")
        print("  set ADMIN_PASSWORD=YourStrongPassword1!")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role == "admin":
                print(f"Admin user already exists: {email}")
            else:
                print(
                    f"ERROR: Email {email} is already registered"
                    f" as role '{existing.role}'"
                )
                sys.exit(1)
            return

        admin = User(
            email=email,
            phone=phone,
            password_hash=hash_password(password),
            role="admin",
            status="approved",
        )
        db.add(admin)
        db.commit()
        print(f"Admin user created successfully: {email}")
        print("You can now log in and approve merchants/drivers.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
