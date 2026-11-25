"""Local operator account management. No administrator HTTP surface."""
import argparse
from getpass import getpass
import secrets
import time
import app


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    role = sub.add_parser("role")
    role.add_argument("email")
    role.add_argument("role", choices=["admin", "editor", "viewer"])
    create = sub.add_parser("create-user")
    create.add_argument("email")
    create.add_argument("--role", choices=["admin", "editor", "viewer"], default="viewer")
    args = parser.parse_args()
    with app.connect() as db:
        if args.command == "role":
            cursor = db.execute("UPDATE users SET role=? WHERE email=?", (args.role, args.email.lower()))
            if not cursor.rowcount:
                parser.error("Account not found")
            db.execute("DELETE FROM sessions WHERE user_id=(SELECT id FROM users WHERE email=?)", (args.email.lower(),))
            print("Role updated. Existing sessions revoked.")
        else:
            password = getpass("New password (12+ characters): ")
            if not 12 <= len(password) <= 1024 or "@" not in args.email:
                parser.error("Invalid email or password length")
            salt = secrets.token_hex(16)
            db.execute("INSERT INTO users(email,password_hash,salt,role,created_at) VALUES (?,?,?,?,?)", (args.email.lower(), app.password_hash(password, salt), salt, args.role, int(time.time())))
            print("Account created.")


if __name__ == "__main__":
    main()
