"""
Allow using SQLite in environments where CPython was built without the _sqlite3 module.

By installing `pysqlite3-binary` and aliasing it to the standard library name,
`import sqlite3` will succeed and Django's sqlite backend will work.
"""
try:
    import sys
    import pysqlite3 as sqlite3  # type: ignore
    # Ensure both module names resolve as expected
    sys.modules.setdefault("sqlite3", sqlite3)
    sys.modules.setdefault("_sqlite3", sqlite3)
except Exception:
    # If pysqlite3 isn't installed, do nothing; the normal import path will apply.
    pass
