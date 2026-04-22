from fastapi import APIRouter, Request

from app.deps import database_session_dependency
from app.schemas import TestResultPartialInput
from app.services.test_result_service import (
    list_recent_test_results,
    upsert_partial_test_result,
)


tester_router = APIRouter(prefix="/tester", tags=["tester"])


@tester_router.get("/dashboard")
def render_tester_dashboard(
    request: Request,
    database_session: database_session_dependency,
):
    recent_test_results = list_recent_test_results(database_session=database_session, limit=20)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "tester_dashboard.html",
        {
            "request": request,
            "page_title": "Tester Dashboard",
            "recent_test_results": recent_test_results,
        },
    )


@tester_router.post("/rows/upsert")
def upsert_tester_row(
    test_result_partial_input: TestResultPartialInput,
    database_session: database_session_dependency,
):
    test_result = upsert_partial_test_result(
        database_session=database_session,
        test_result_partial_input=test_result_partial_input,
    )
    return {
        "message": "Row upserted.",
        "id": test_result.id,
        "key_1": test_result.key_1,
        "key_2": test_result.key_2,
        "key_3": test_result.key_3,
    }

