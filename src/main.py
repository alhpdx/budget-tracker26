"""
Simple CLI budget tracker starter

Usage:
  - Add a transaction:
      python -m src.main add --amount 12.50 --category groceries --note "coffee"
  - List transactions:
      python -m src.main list
  - Show total balance:
      python -m src.main total

Data is stored in budget_data.json in the repository root.
This is a minimal starter. Extend as needed (persistence, tests, web UI, etc.).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List

DATA_FILE = Path("budget_data.json")


@dataclass
class Transaction:
    amount: float
    category: str
    note: str
    timestamp: str


def load_data() -> List[Transaction]:
    if not DATA_FILE.exists():
        return []
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return [Transaction(**r) for r in raw]
    except Exception:
        return []


def save_data(transactions: List[Transaction]) -> None:
    DATA_FILE.write_text(json.dumps([asdict(t) for t in transactions], indent=2), encoding="utf-8")


def add_transaction(amount: float, category: str, note: str) -> Transaction:
    t = Transaction(amount=amount, category=category, note=note, timestamp=datetime.utcnow().isoformat())
    txs = load_data()
    txs.append(t)
    save_data(txs)
    return t


def list_transactions() -> List[Transaction]:
    return load_data()


def total_balance() -> float:
    return sum(t.amount for t in load_data())


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="budget-tracker")
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Add a transaction")
    p_add.add_argument("--amount", type=float, required=True)
    p_add.add_argument("--category", type=str, default="uncategorized")
    p_add.add_argument("--note", type=str, default="")

    sub.add_parser("list", help="List transactions")
    sub.add_parser("total", help="Show total balance")
    sub.add_parser("clear", help="Clear all transactions (destructive)")

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)

    if args.cmd == "add":
        t = add_transaction(args.amount, args.category, args.note)
        print("Added:", asdict(t))
        return 0

    if args.cmd == "list":
        for t in list_transactions():
            print(f"{t.timestamp}  {t.amount:+.2f}  [{t.category}] {t.note}")
        return 0

    if args.cmd == "total":
        print(f"Total: {total_balance():.2f}")
        return 0

    if args.cmd == "clear":
        confirm = input("Type YES to permanently delete all transactions: ")
        if confirm == "YES":
            save_data([])
            print("Cleared all transactions.")
        else:
            print("Aborted.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
