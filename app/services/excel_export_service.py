from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.services.test_result_service import list_recent_test_results


def build_test_result_workbook(database_session: Session) -> Workbook:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "test_results"

    header_names = [
        "id",
        "key_1",
        "key_2",
        "key_3",
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
        "created_at",
        "updated_at",
    ]
    worksheet.append(header_names)

    for test_result in list_recent_test_results(database_session=database_session, limit=1000):
        worksheet.append(
            [
                test_result.id,
                test_result.key_1,
                test_result.key_2,
                test_result.key_3,
                test_result.field_01,
                test_result.field_02,
                test_result.field_03,
                test_result.field_04,
                test_result.field_05,
                test_result.field_06,
                test_result.field_07,
                test_result.field_08,
                test_result.field_09,
                test_result.field_10,
                test_result.low_test_started_at,
                test_result.low_test_ended_at,
                test_result.low_test_delta,
                test_result.high_test_started_at,
                test_result.high_test_ended_at,
                test_result.high_test_delta,
                str(test_result.created_at),
                str(test_result.updated_at),
            ]
        )

    return workbook

