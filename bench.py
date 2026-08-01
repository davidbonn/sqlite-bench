"""
    benchmark program
"""

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time

from faker import Faker
import progressbar

from misc import cursor_for
from worker import Worker, open_db


def note_json(json_path: str, type_str: str, workers: int, count: int, value: float):
    try:
        with open(json_path, "r") as f:
            data = f.read()
            data = json.loads(data)
    except FileNotFoundError:
        data = dict()

    data[type_str] = {
        "workers": workers,
        "value": value,
        "when": time.ctime(time.time()),
        "count": count,
    }

    with open(json_path, "w") as f:
        f.write(json.dumps(data, indent=4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=str, default="sample.db")
    ap.add_argument("--verbose", action="store_true", default=False)
    ap.add_argument("--count", type=int, default=10000)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--readonly", action='store_true', default=False)
    ap.add_argument("--json", type=str, default="results.json")
    ap.add_argument("--type", type=str, default="single")
    args = ap.parse_args()

    if not Path(args.db).exists():
        print(f"Database {args.db} does not exist!")
        exit(1)

    db = open_db(args.db)

    rc = 0.0

    max_user = db.execute("SELECT MAX(id) FROM users;").fetchone()[0]
    max_topic = db.execute("SELECT MAX(id) FROM topics;").fetchone()[0]

    db.close()
    w = Worker(args)
    w.setup(max_user, max_topic)
    rc = w.run(args.type)

    note_json(args.json, args.type, args.workers, args.count, rc)


if __name__ == "__main__":
    main()