#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TIMEZONE = ZoneInfo("Asia/Seoul")
LAST_MODIFIED_RE = re.compile(
    r"^(?P<prefix>\s*last_modified_at\s*:\s*).*$",
    re.MULTILINE,
)


def update_last_modified(path: Path, now: datetime) -> bool:
    content = path.read_text(encoding="utf-8")
    new_value = now.strftime("%Y-%m-%d %H:%M:%S %z")

    updated, count = LAST_MODIFIED_RE.subn(
        rf"\g<prefix>{new_value}",
        content,
        count=1,
    )
    if count == 0:
        return False

    path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update only the last_modified_at field in a file."
    )
    parser.add_argument("path", type=Path, help="File path to update")
    args = parser.parse_args()

    if not args.path.is_file():
        raise FileNotFoundError(f"{args.path} is not a file")

    if not update_last_modified(args.path, datetime.now(TIMEZONE)):
        raise ValueError(f"{args.path} does not contain last_modified_at")

    print(f"Updated last_modified_at in {args.path}")


if __name__ == "__main__":
    main()
