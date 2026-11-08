"""First local Studio utility: index legacy JSON and search it quickly."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.studio_store import StudioStore, import_json_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram Channel Studio local index")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index = subparsers.add_parser("index", help="Import an existing JSON database into SQLite")
    index.add_argument("json_path", type=Path)
    index.add_argument("sqlite_path", type=Path)

    search = subparsers.add_parser("search", help="Search indexed messages")
    search.add_argument("sqlite_path", type=Path)
    search.add_argument("--text")
    search.add_argument("--channel")
    search.add_argument("--from-date", dest="date_from")
    search.add_argument("--to-date", dest="date_to")
    search.add_argument("--media", action="store_true")
    search.add_argument("--limit", type=int, default=50)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "index":
        result = import_json_file(args.json_path, args.sqlite_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    rows = StudioStore(args.sqlite_path).search_messages(
        text=args.text, channel_id=args.channel, date_from=args.date_from,
        date_to=args.date_to, has_media=True if args.media else None, limit=args.limit,
    )
    for row in rows:
        snippet = (row.get("raw_text") or row.get("text") or "").replace("\n", " ")[:180]
        print(f"[{row['date']}] {row['channel_title']} #{row['message_id']} — {snippet}")


if __name__ == "__main__":
    main()
