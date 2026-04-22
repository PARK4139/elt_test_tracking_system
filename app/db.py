from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import app_settings


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
    from app import models

    models.Base.metadata.create_all(bind=engine)
    _ensure_user_account_columns()
    _ensure_test_result_columns()


def _ensure_user_account_columns() -> None:
    expected_columns = {
        "display_name": "TEXT",
        "phone_number": "TEXT",
        "company_name": "TEXT",
        "department_name": "TEXT",
        "is_approved": "INTEGER DEFAULT 1",
    }
    with engine.begin() as connection:
        existing_column_names = {
            row[1] for row in connection.execute(text("PRAGMA table_info(user_account)"))
        }
        for column_name, column_type in expected_columns.items():
            if column_name in existing_column_names:
                continue
            connection.execute(
                text(f"ALTER TABLE user_account ADD COLUMN {column_name} {column_type}")
            )


def _ensure_test_result_columns() -> None:
    expected_columns = {
        "submission_id": "TEXT",
        "data_writer_name": "TEXT",
        "is_reviewed": "INTEGER DEFAULT 0",
    }
    with engine.begin() as connection:
        existing_column_names = {
            row[1] for row in connection.execute(text("PRAGMA table_info(test_result)"))
        }
        for column_name, column_type in expected_columns.items():
            if column_name in existing_column_names:
                continue
            connection.execute(
                text(f"ALTER TABLE test_result ADD COLUMN {column_name} {column_type}")
            )
