
import sqlite3
from contextlib import contextmanager


@contextmanager
def cursor_for(conn, do_commit=False):
    cursor = conn.cursor()
    try:
        if do_commit:
            cursor.execute("BEGIN IMMEDIATE TRANSACTION")

        yield cursor

    except sqlite3.OperationalError as e:
        if do_commit:
            cursor.execute("ROLLBACK")
            print(f"sqlite3 write failed: {e}")

    finally:
        if do_commit:
            conn.commit()

        cursor.close()
