from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import TestResult, get_utc_now_datetime
from app.schemas import TestResultPartialInput


PARTIAL_UPDATE_FIELD_NAMES = [
    "submission_id",
    "data_writer_name",
    "field_01",
    "field_02",
    "field_03",
    "field_04",
    "field_05",
    "field_06",
    "field_07",
    "field_08",
    "field_09",
    "field_10",
    "low_test_started_at",
    "low_test_ended_at",
    "low_test_delta",
    "high_test_started_at",
    "high_test_ended_at",
    "high_test_delta",
]


def _strip_if_string(value):
    if isinstance(value, str):
        return value.strip()
    return value


def upsert_partial_test_result(
    database_session: Session,
    test_result_partial_input: TestResultPartialInput,
) -> TestResult:
    key_1 = _strip_if_string(test_result_partial_input.key_1)
    key_2 = _strip_if_string(test_result_partial_input.key_2)
    key_3 = _strip_if_string(test_result_partial_input.key_3)
    if not key_1 or not key_2 or not key_3:
        raise ValueError("key_1, key_2, and key_3 must be non-empty after trimming.")

    existing_test_result = database_session.scalar(
        select(TestResult).where(
            TestResult.key_1 == key_1,
            TestResult.key_2 == key_2,
            TestResult.key_3 == key_3,
        )
    )

    if existing_test_result is None:
        existing_test_result = TestResult(
            key_1=key_1,
            key_2=key_2,
            key_3=key_3,
        )
        database_session.add(existing_test_result)

    for field_name in PARTIAL_UPDATE_FIELD_NAMES:
        new_value = _strip_if_string(getattr(test_result_partial_input, field_name))
        if new_value is not None:
            setattr(existing_test_result, field_name, new_value)

    try:
        database_session.commit()
    except IntegrityError as exception:
        database_session.rollback()
        raise ValueError("A row with the same key_1, key_2, key_3 already exists.") from exception
    database_session.refresh(existing_test_result)
    return existing_test_result


def list_recent_test_results(database_session: Session, limit: int = 20) -> list[TestResult]:
    result_rows = database_session.scalars(
        select(TestResult).order_by(TestResult.updated_at.desc()).limit(limit)
    )
    return list(result_rows)


def _get_test_result_or_raise(database_session: Session, test_result_id: int) -> TestResult:
    test_result = database_session.get(TestResult, test_result_id)
    if test_result is None:
        raise LookupError("Test result not found.")
    return test_result


def _commit_and_refresh(database_session: Session, test_result: TestResult) -> TestResult:
    database_session.commit()
    database_session.refresh(test_result)
    return test_result


def _to_delta_string(started_at: datetime, ended_at: datetime) -> str:
    return str(ended_at - started_at)


def mark_low_test_start(database_session: Session, test_result_id: int) -> TestResult:
    test_result = _get_test_result_or_raise(database_session, test_result_id)
    if test_result.low_test_started_at is not None:
        raise ValueError("low_test/start cannot run twice.")
    test_result.low_test_started_at = get_utc_now_datetime()
    return _commit_and_refresh(database_session, test_result)


def mark_low_test_end(database_session: Session, test_result_id: int) -> TestResult:
    test_result = _get_test_result_or_raise(database_session, test_result_id)
    if test_result.low_test_started_at is None:
        raise ValueError("low_test/end requires low_test/start.")
    if test_result.low_test_ended_at is not None:
        raise ValueError("low_test/end cannot run twice.")
    test_result.low_test_ended_at = get_utc_now_datetime()
    test_result.low_test_delta = _to_delta_string(
        test_result.low_test_started_at,
        test_result.low_test_ended_at,
    )
    return _commit_and_refresh(database_session, test_result)


def mark_high_test_start(database_session: Session, test_result_id: int) -> TestResult:
    test_result = _get_test_result_or_raise(database_session, test_result_id)
    if test_result.high_test_started_at is not None:
        raise ValueError("high_test/start cannot run twice.")
    test_result.high_test_started_at = get_utc_now_datetime()
    return _commit_and_refresh(database_session, test_result)


def mark_high_test_end(database_session: Session, test_result_id: int) -> TestResult:
    test_result = _get_test_result_or_raise(database_session, test_result_id)
    if test_result.high_test_started_at is None:
        raise ValueError("high_test/end requires high_test/start.")
    if test_result.high_test_ended_at is not None:
        raise ValueError("high_test/end cannot run twice.")
    test_result.high_test_ended_at = get_utc_now_datetime()
    test_result.high_test_delta = _to_delta_string(
        test_result.high_test_started_at,
        test_result.high_test_ended_at,
    )
    return _commit_and_refresh(database_session, test_result)
