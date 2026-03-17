from sqlalchemy import event
from sqlalchemy.engine import Engine


def configure_sqlite_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA temp_store=MEMORY;")
        cursor.close()
