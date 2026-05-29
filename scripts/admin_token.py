"""Generate local Ithildin admin bearer tokens without writing secrets to disk."""

from __future__ import annotations

import argparse
import secrets
import string
import sys

DEFAULT_BYTES = 32
TOKEN_PREFIX = "ithildin_admin_"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bytes",
        type=int,
        default=DEFAULT_BYTES,
        help="number of random bytes before URL-safe encoding",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="print only the token value instead of an .env assignment",
    )
    args = parser.parse_args()

    if args.bytes < 24:
        print("admin token generation requires at least 24 random bytes", file=sys.stderr)
        return 2

    token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(args.bytes)}"
    if not _is_shell_safe_token(token):
        print("generated token failed local safety validation", file=sys.stderr)
        return 1

    if args.raw:
        print(token)
    else:
        print(f"ITHILDIN_ADMIN_TOKEN={token}")
    return 0


def _is_shell_safe_token(token: str) -> bool:
    allowed = set(string.ascii_letters + string.digits + "-_")
    return bool(token) and all(character in allowed for character in token)


if __name__ == "__main__":
    raise SystemExit(main())
