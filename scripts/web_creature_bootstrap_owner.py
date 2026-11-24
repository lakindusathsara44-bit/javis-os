"""One-time local bootstrap for the first WEB CREATURE owner.

Run only from a trusted machine with direct access to the private database:
    python scripts/web_creature_bootstrap_owner.py --enable-bootstrap --database /secure/path/creature-auth.sqlite3

No password is accepted through command-line arguments or environment variables.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.creature.accounts import AccountStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the first WEB CREATURE owner account.")
    parser.add_argument("--database", required=True, help="Private SQLite database path outside public/static directories.")
    parser.add_argument(
        "--enable-bootstrap",
        action="store_true",
        help="Explicitly authorize the one-time first-owner bootstrap operation.",
    )
    args = parser.parse_args()

    if not args.enable_bootstrap:
        parser.error("--enable-bootstrap is required; no owner is created by default.")

    database = Path(args.database).expanduser().resolve()
    print(f"WEB CREATURE account database: {database}")
    confirmation = input("Type CREATE FIRST OWNER to continue: ").strip()
    if confirmation != "CREATE FIRST OWNER":
        print("Bootstrap cancelled.")
        return 2

    email = input("Owner email: ").strip()
    password = getpass.getpass("Owner password (12+ characters): ")
    confirm = getpass.getpass("Confirm owner password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 2

    try:
        store = AccountStore(database)
        account = store.bootstrap_owner(email, password, bootstrap_enabled=True)
    except (ValueError, PermissionError, OSError) as exc:
        print(f"Owner bootstrap failed: {exc}", file=sys.stderr)
        return 1

    print(f"First WEB CREATURE owner created: {account.email}")
    print("Bootstrap is now permanently closed for this database.")
    print("Protect the database and its backups; do not place it in a public/static directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
