"""
    creates blank sample database
"""

import argparse
from pathlib import Path
import secrets
import sqlite3

from faker import Faker
import progressbar

from misc import cursor_for


bar_widgets = [
    progressbar.Percentage(),
    " ",
    progressbar.GranularBar(),
    " ",
    progressbar.ETA(),]


def mk_users(db, count:int, verbose:bool):
    print("Creating users...")

    with cursor_for(db, do_commit=True) as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                password TEXT)
            """
        )

        fake = Faker()
        with progressbar.ProgressBar(widgets=bar_widgets, maxval=count) as bar:
            for i in range(count):
                bar.update(i)
                name = fake.name()
                email = fake.email()
                password = secrets.token_hex(16)
                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                    (name, email, password),
                )


def mk_topics(db, count:int, verbose:bool):
    print("Creating topics...")

    with cursor_for(db, do_commit=True) as cursor:
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT
                )
            """
        )

        fake = Faker()
        with progressbar.ProgressBar(widgets=bar_widgets, maxval=count) as bar:
            for i in range(count):
                bar.update(i)
                cursor.execute("INSERT INTO topics (title) VALUES (?)", (fake.sentence(),))


def mk_posts(db, count:int, verbose:bool):
    print("Creating posts...")

    with cursor_for(db, do_commit=True) as cursor:
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    topic_id INTEGER,
                    headers TEXT,
                    body TEXT
                )
            """
        )

        fake = Faker()
        max_users = count // 100
        max_topics = count // 10

        with progressbar.ProgressBar(widgets=bar_widgets, maxval=count) as bar:
            for i in range(count):
                bar.update(i)
                cursor.execute(
                    "INSERT INTO posts (user_id, topic_id, headers, body) VALUES (?, ?, ?, ?)",
                    (fake.random_int(min=1, max=max_users), fake.random_int(min=1, max=max_topics), fake.json(), fake.text())
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="sample.db")
    parser.add_argument("--verbose", action="store_true", default=False)
    parser.add_argument("--rows", type=int, default=1_000)
    args = parser.parse_args()

    Path(args.db).unlink(missing_ok=True)

    db = sqlite3.connect(args.db, timeout=10.0)
    db.isolation_level = None
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("PRAGMA synchronous=NORMAL;")
    db.execute("PRAGMA journal_size_limit=16777216;")

    mk_users(db, args.rows // 100, args.verbose)
    mk_topics(db, args.rows // 10, args.verbose)
    mk_posts(db, args.rows, args.verbose)


if __name__ == "__main__":
    main()
