from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from elt_test_tracking_system.app.config import app_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    app_settings.sqlite_database_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(database_api_connection, _connection_record) -> None:
    cursor = database_api_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


session_local = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


def get_database_session() -> Iterator[Session]:
    database_session = session_local()
    try:
        yield database_session
    finally:
        database_session.close()


def initialize_database() -> None:
    from elt_test_tracking_system.app import models

    models.Base.metadata.create_all(bind=engine)
