from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.services.test_result_service import list_recent_test_results


def _datetime_to_isoformat(value):
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def build_test_result_workbook(database_session: Session) -> Workbook:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "test_results"

    header_names = [
        "양식제출ID",
        "데이터생성시각",
        "성함(데이터작성자)",
        "key_seg 1",
        "key_seg 2",
        "key_seg 3",
        "temp_col 01",
        "temp_col 02",
        "temp_col 03",
        "temp_col 04",
        "temp_col 05",
        "temp_col 06",
        "temp_col 07",
        "temp_col 08",
        "temp_col 09",
        "temp_col 10",
        "저온시험 시작",
        "저온시험 종료",
        "저온시험 소요시간",
        "고온시험 시작",
        "고온시험 종료",
        "고온시험 소요시간",
        "데이터수정시각",
    ]
    worksheet.append(header_names)

    for test_result in list_recent_test_results(database_session=database_session, limit=1000):
        worksheet.append(
            [
                test_result.submission_id,
                _datetime_to_isoformat(test_result.created_at),
                test_result.data_writer_name,
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
                _datetime_to_isoformat(test_result.low_test_started_at),
                _datetime_to_isoformat(test_result.low_test_ended_at),
                test_result.low_test_delta,
                _datetime_to_isoformat(test_result.high_test_started_at),
                _datetime_to_isoformat(test_result.high_test_ended_at),
                test_result.high_test_delta,
                _datetime_to_isoformat(test_result.updated_at),
            ]
        )

    return workbook
