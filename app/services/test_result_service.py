from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TestResult
from app.schemas import TestResultPartialInput


PARTIAL_UPDATE_FIELD_NAMES = [
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


def upsert_partial_test_result(
    database_session: Session,
    test_result_partial_input: TestResultPartialInput,
) -> TestResult:
    existing_test_result = database_session.scalar(
        select(TestResult).where(
            TestResult.key_1 == test_result_partial_input.key_1,
            TestResult.key_2 == test_result_partial_input.key_2,
            TestResult.key_3 == test_result_partial_input.key_3,
        )
    )

    if existing_test_result is None:
        existing_test_result = TestResult(
            key_1=test_result_partial_input.key_1,
            key_2=test_result_partial_input.key_2,
            key_3=test_result_partial_input.key_3,
        )
        database_session.add(existing_test_result)

    for field_name in PARTIAL_UPDATE_FIELD_NAMES:
        new_value = getattr(test_result_partial_input, field_name)
        if new_value is not None:
            setattr(existing_test_result, field_name, new_value)

    database_session.commit()
    database_session.refresh(existing_test_result)
    return existing_test_result


def list_recent_test_results(database_session: Session, limit: int = 20) -> list[TestResult]:
    result_rows = database_session.scalars(
        select(TestResult).order_by(TestResult.updated_at.desc()).limit(limit)
    )
    return list(result_rows)

