"""Create an administrator without a default or hard-coded password."""

import getpass
from sqlalchemy import select
from app.database.connection import Base, engine, SessionLocal, User
from app.core.security import hash_password
from app.core.password_policy import valid_new_password, PASSWORD_REQUIREMENT
from app.data.seed import seed
from pathlib import Path
from app.database.migrations.numeric_ids import upgrade


def main():
    upgrade(engine, Path(__file__).resolve().parents[2] / 'storage/backups', apply=True)
    seed()
    email = input("Admin email: ").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise SystemExit("Invalid email.")
    name = input("Display name: ").strip() or "Admin"
    print(PASSWORD_REQUIREMENT)
    password = getpass.getpass("Password: ")
    if not valid_new_password(password):
        raise SystemExit(PASSWORD_REQUIREMENT)
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Account already exists. No account was changed.")
        db.add(
            User(
                email=email,
                name=name[:80],
                password_hash=hash_password(password),
                role="admin",
            )
        )
        db.commit()
    print("Administrator created.")


if __name__ == "__main__":
    main()
