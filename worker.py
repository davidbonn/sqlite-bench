"""
    worker class used by bench.py
"""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import sqlite3
import time

import progressbar
from faker import Faker

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


class Worker:
    def __init__(self, args):
        self.verbose = args.verbose
        self.dbname = args.db
        self.count = args.count
        self.workers=  args.workers
        self.readonly = args.readonly

        self.max_users = None
        self.max_topics = None

    def setup(self, max_users:int, max_topics:int):
        self.max_users = max_users
        self.max_topics = max_topics

    def run(self, mode:str):
        match mode:
            case "single":
                return self.single()
            case "multi":
                return self.parallel(ProcessPoolExecutor)
            case "thread":
                return self.parallel(ThreadPoolExecutor)
            case _:
                print(f"Unknown mode {mode}")
                exit(1)

    def readers(self, db, user_id:int, topic_id:int):
        with cursor_for(db, do_commit=False) as cursor:
            messages = cursor.execute(
                "SELECT p.id, p.headers, t.title FROM posts p, topics t WHERE p.topic_id=? AND p.topic_id = t.id ORDER BY p.id",
                (topic_id,)
            ).fetchall()

            for i in range(len(messages)):
                msg = cursor.execute("SELECT body FROM posts WHERE id=?", (messages[i][0],)).fetchone()[0]

    def writers(self, db, user_id:int, topic_id:int, fake):
        if self.readonly:
            return

        with cursor_for(db, do_commit=True) as cursor:
            cursor.execute(
                "INSERT INTO posts (user_id, topic_id, headers, body) VALUES (?, ?, ?, ?)",
                (user_id, topic_id, fake.json(), fake.text())
            )

    def db_op(self, fake):
        db = open_db(self.dbname)
        user_id = fake.random_int(min=1, max=self.max_users)
        topic_id = fake.random_int(min=1, max=self.max_topics)
        self.readers(db, user_id, topic_id)
        self.writers(db, user_id, topic_id, fake)
        db.close()

    def single(self) -> float:
        faker = Faker()
        start = time.perf_counter()
        with progressbar.ProgressBar(widgets=bar_widgets, maxval=self.count) as bar:
            for i in range(self.count):
                bar.update(i)
                self.db_op(faker)

        return time.perf_counter() - start

    def parallel(self, my_executor) -> float:
        fake = Faker()

        start = time.perf_counter()
        with my_executor(max_workers=self.workers) as executor:
            futures = [executor.submit(self.db_op, fake) for _ in range(self.count)]

            with progressbar.ProgressBar(widgets=bar_widgets, maxval=self.count) as bar:
                i = 0
                for future in as_completed(futures):
                    bar.update(i)
                    i += 1
                    _ = future.result()

        return time.perf_counter() - start
