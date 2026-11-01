import getpass
import sys

from sqlalchemy import select

from .db import SessionLocal
from .models import AdminUser
from .passwords import hash_password


def main() -> None:
    username = input("Admin username: ").strip()
    if not username:
        sys.exit("username required")
    password = getpass.getpass("Password (min 12 chars): ")
    confirm = getpass.getpass("Repeat password: ")
    if password != confirm:
        sys.exit("passwords do not match")
    if len(password) < 12:
        sys.exit("password too short")
    with SessionLocal() as db:
        q = select(AdminUser).where(AdminUser.username == username)
        if db.scalar(q):
            sys.exit("user already exists")
        db.add(AdminUser(username=username, password_hash=hash_password(password)))
        db.commit()
    print("admin created:", username)


if __name__ == "__main__":
    main()
