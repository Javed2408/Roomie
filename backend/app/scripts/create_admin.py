"""Create an administrator account, or promote an existing account.

    python -m app.scripts.create_admin someone@example.com

The password is typed at a hidden prompt, so it never appears on screen,
in the command history or in a file. There is deliberately no way to
become an administrator through the website.
"""

import getpass
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.security import hash_password, password_problem
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import normalise_email


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m app.scripts.create_admin <email>")
        return 2
    email = normalise_email(sys.argv[1])

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            user.role = UserRole.ADMIN
            db.commit()
            print(f"{email} already had an account and is now an administrator.")
            return 0

        password = getpass.getpass("Choose a password: ")
        if password != getpass.getpass("Type it again: "):
            print("The two passwords did not match. Nothing was created.")
            return 1
        problem = password_problem(password)
        if problem:
            print(f"That password is not acceptable: {problem}")
            return 1

        now = datetime.now(UTC)
        db.add(
            User(
                email=email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                # Created by hand by someone with server access.
                email_verified_at=now,
                terms_accepted_at=now,
            )
        )
        db.commit()
        print(f"Administrator account created for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
