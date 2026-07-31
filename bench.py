"""
    benchmark program
"""

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sqlite3
import time

from faker import Faker
import progressbar

from misc import cursor_for


bar_widgets = [
    progressbar.Percentage(),
    " ",
    progressbar.GranularBar(),
    " ",
    progressbar.ETA(),]


def open_db(db_path:str):
    db = sqlite3.connect(db_path, timeout=10.0)

    db.isolation_level = None
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("PRAGMA synchronous=NORMAL;")
    db.execute("PRAGMA journal_size_limit=16777216;")

    return db


def db_op(db_name, db, max_user:int, max_topic:int, fake):
    opened = False
    if db is None:
        db = open_db(db_name)
        opened = True

    with cursor_for(db, do_commit=False) as cursor:
        user_id = fake.random_int(min=1, max=max_user)
        topic_id = fake.random_int(min=1, max=max_topic)

        messages = cursor.execute(
            "SELECT p.id, p.headers, t.title FROM posts p, topics t WHERE p.topic_id=? AND p.topic_id = t.id ORDER BY p.id",
            (topic_id,)
        ).fetchall()

        for i in range(len(messages)):
            msg = cursor.execute("SELECT body FROM posts WHERE id=?", (messages[i][0],)).fetchone()[0]

    with cursor_for(db, do_commit=True) as cursor:
        cursor.execute(
            "INSERT INTO posts (user_id, topic_id, headers, body) VALUES (?, ?, ?, ?)",
            (user_id, topic_id, fake.json(), fake.text())
        )

    if opened:
        db.close()


def single_work(db_name:str, count:int, verbose:bool, max_user:int, max_topic:int) -> float:
    fake = Faker()
    db = open_db(db_name)

    start = time.perf_counter()
    with progressbar.ProgressBar(widgets=bar_widgets, maxval=count) as bar:
        for i in range(count):
            bar.update(i)
            db_op(db_name, db, max_user, max_topic, fake)

    return time.perf_counter() - start

def parallel_work(my_executor, db_name, count:int, verbose:bool, workers:int, max_user:int, max_topic:int) -> float:
    fake = Faker()

    start = time.perf_counter()
    with my_executor(max_workers=workers) as executor:
        futures = [executor.submit(db_op, db_name, None, max_user, max_topic, fake) for _ in range(count)]

        with progressbar.ProgressBar(widgets=bar_widgets, maxval=count) as bar:
            i = 0
            for future in as_completed(futures):
                bar.update(i)
                i += 1
                _ = future.result()

    return time.perf_counter() - start



def thread_work(db_name, count:int, verbose:bool, workers:int, max_user:int, max_topic:int) -> float:
    return parallel_work(ThreadPoolExecutor, db_name, count, verbose, workers, max_user, max_topic)


def multi_work(db_name, count:int, verbose:bool, workers:int, max_user:int, max_topic:int) -> float:
    return parallel_work(ProcessPoolExecutor, db_name, count, verbose, workers, max_user, max_topic)


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

    match args.type:
        case "single":
            rc = single_work(args.db, args.count, args.verbose, max_user, max_topic)

        case "thread":
            rc = thread_work(args.db, args.count, args.verbose, args.workers, max_user, max_topic)

        case "multi":
            rc = multi_work(args.db, args.count, args.verbose, args.workers, max_user, max_topic)

        case _:
            print(f"Unknown type {args.type}")
            exit(1)

    note_json(args.json, args.type, args.workers, args.count, rc)


if __name__ == "__main__":
    main()