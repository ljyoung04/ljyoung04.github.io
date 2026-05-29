#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


POSTS_DIR = Path("_posts")
TIMEZONE = ZoneInfo("Asia/Seoul")


def slugify(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^0-9a-zA-Z가-힣._-]+", "", slug)
    slug = slug.strip(".-_")

    if not slug:
        raise ValueError("title must contain at least one usable character")

    return slug


def build_post(title: str, now: datetime) -> tuple[Path, str]:
    slug = slugify(title)
    filename = f"{now:%Y-%m-%d}-{slug}.md"
    post_path = POSTS_DIR / f"{now:%Y}" / filename
    date = now.strftime("%Y-%m-%d %H:%M:%S %z")

    content = f"""---
title: {post_path.stem}
date: {date}
last_modified_at: {date}
categories: []
---
"""

    return post_path, content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a Chirpy post template in the _posts directory."
    )
    parser.add_argument("title", help="Post title used in YYYY-MM-DD-TITLE.md")
    args = parser.parse_args()

    now = datetime.now(TIMEZONE)
    post_path, content = build_post(args.title, now)

    post_path.parent.mkdir(parents=True, exist_ok=True)
    if post_path.exists():
        raise FileExistsError(f"{post_path} already exists")

    post_path.write_text(content, encoding="utf-8")

    print(f"Created {post_path}")


if __name__ == "__main__":
    main()
