import os
import sys

import db
import security
from accounts import ACCOUNTS

HERE = os.path.dirname(os.path.abspath(__file__))


def ensure_schema(reset):
    if db.BACKEND == "mysql":
        return
    exists = os.path.exists(db.SQLITE_PATH) and db.one("SELECT name FROM sqlite_master WHERE name = 'users'")
    if reset or not exists:
        db.init_schema(os.path.join(HERE, "schema_sqlite.sql"))
        print("Created a fresh SQLite database at " + db.SQLITE_PATH)


def seed_accounts():
    for account in ACCOUNTS:
        hashed = security.hash_password(account["password"])
        existing = db.one("SELECT id FROM users WHERE email = ?", account["email"])
        if existing:
            db.execute("UPDATE users SET password_hash = ?, status = 'ACTIVE' WHERE id = ?", hashed, existing["id"])
            action = "Updated"
        else:
            db.execute(
                "INSERT INTO users (role, employee_no, first_name, last_name, email, password_hash, status) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')",
                account["role"], account["employee_no"], account["first_name"], account["last_name"], account["email"], hashed,
            )
            action = "Created"
        print(action + " " + account["role"].ljust(8) + account["email"].ljust(28) + account["password"])


def main():
    ensure_schema("--reset" in sys.argv)
    seed_accounts()


if __name__ == "__main__":
    main()
