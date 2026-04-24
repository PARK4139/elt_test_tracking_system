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
        "양식제출자",
        "업체명",
        "col_key_seg",
        "공정번호",
        "col 1",
        "col_2",
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
