from fastapi import APIRouter, Request

from app.auth import ROLE_MASTER_ADMIN
from app.deps import current_role_name_dependency, database_session_dependency
from app.services.test_result_service import list_recent_test_results


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/dashboard")
def render_admin_dashboard(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
):
    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "page_title": "Admin Dashboard",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
        },
    )
