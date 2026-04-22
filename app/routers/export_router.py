from io import BytesIO
import os

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.auth import ROLE_ADMIN, ROLE_MASTER_ADMIN, ensure_role_allowed
from app.deps import current_role_name_dependency, database_session_dependency
from app.services.excel_export_service import build_test_result_workbook


export_router = APIRouter(prefix="/admin/export", tags=["export"])


@export_router.get("/xlsx")
def export_test_results_as_excel(
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
):
    qc_mode_enabled = os.getenv("QC_MODE", "True").strip().lower() in {"1", "true", "yes", "on"}
    if not qc_mode_enabled:
        ensure_role_allowed(current_role_name, {ROLE_ADMIN, ROLE_MASTER_ADMIN})
    workbook = build_test_result_workbook(database_session=database_session)
    output_stream = BytesIO()
    workbook.save(output_stream)
    output_stream.seek(0)
    return StreamingResponse(
        output_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=test_results.xlsx"},
    )
