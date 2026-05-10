from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from app.services.checklist_template_service import build_model_template_payload_map
from app.services.test_result_service import list_recent_test_results


def _datetime_to_isoformat(value):
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _worksheet_header_names() -> list[str]:
    return [
        "양식제출ID",
        "데이터생성시각",
        "업체명",
        "양식제출자",
        "시험양식명",
        "시험 항목 01",
        "시험 항목 02",
        "시험 항목 03",
        "시험 항목 04",
        "시험 항목 05",
        "시험 항목 06",
        "시험 항목 07",
        "시험 항목 08",
        "시험 항목 09",
        "시험 항목 10",
        "시험 항목 11",
        "시험 항목 12",
        "시험 항목 13",
        "시험 항목 14",
        "시험 항목 15",
        "적용시점",
        "초품 ECO No.",
        "비고",
        "검사수량",
        "불량수량",
        "rr",
        "임율",
        "비용",
        "데이터수정시각",
    ]


def _test_result_to_excel_row(test_result, model_template_payload_map: dict[str, dict]) -> list:
    template_name = model_template_payload_map.get(
        str(test_result.key_3 or "").strip(),
        {},
    ).get("template_name", "")
    return [
        test_result.form_submission_id,
        _datetime_to_isoformat(test_result.created_at),
        test_result.key_1,
        test_result.key_2,
        template_name,
        test_result.key_3,
        test_result.key_4,
        test_result.field_01,
        test_result.field_02,
        test_result.field_03,
        test_result.field_04,
        test_result.field_05,
        test_result.field_06,
        test_result.field_07,
        test_result.field_10,
        test_result.field_11,
        test_result.field_12,
        test_result.field_13,
        test_result.field_14,
        test_result.field_18,
        test_result.field_15,
        test_result.field_16,
        test_result.field_17,
        test_result.field_08,
        test_result.field_09,
        test_result.field_19,
        test_result.field_20,
        test_result.field_21,
        _datetime_to_isoformat(test_result.updated_at),
    ]


def build_test_result_workbook(database_session: Session) -> Workbook:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "test_results"
    worksheet.append(_worksheet_header_names())

    model_template_payload_map = build_model_template_payload_map(database_session)
    for test_result in list_recent_test_results(database_session=database_session, limit=1000):
        worksheet.append(_test_result_to_excel_row(test_result, model_template_payload_map))

    return workbook


def append_test_results_to_existing_workbook(
    database_session: Session,
    excel_file_path: str,
    sheet_name: str,
    limit: int = 1000,
) -> dict[str, int | str]:
    path = (excel_file_path or "").strip()
    if not path:
        raise ValueError("excel_file_path is required.")
    target_sheet = (sheet_name or "").strip()
    if not target_sheet:
        raise ValueError("sheet_name is required.")

    workbook = load_workbook(path)
    worksheet = (
        workbook[target_sheet]
        if target_sheet in workbook.sheetnames
        else workbook.create_sheet(target_sheet)
    )

    if worksheet.max_row == 1 and worksheet.max_column == 1 and worksheet["A1"].value is None:
        worksheet.append(_worksheet_header_names())

    model_template_payload_map = build_model_template_payload_map(database_session)
    appended = 0
    for test_result in list_recent_test_results(database_session=database_session, limit=limit):
        worksheet.append(_test_result_to_excel_row(test_result, model_template_payload_map))
        appended += 1

    workbook.save(path)
    return {"sheet_name": target_sheet, "appended_rows": appended}
