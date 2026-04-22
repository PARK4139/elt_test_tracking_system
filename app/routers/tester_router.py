from fastapi import APIRouter, HTTPException, Request, status

from app.deps import current_role_name_dependency
from app.deps import database_session_dependency
from app.schemas import TestResultPartialInput
from app.services.test_result_service import (
    list_recent_test_results,
    mark_high_test_end,
    mark_high_test_start,
    mark_low_test_end,
    mark_low_test_start,
    upsert_partial_test_result,
)

tester_router = APIRouter(prefix="/tester", tags=["tester"])


@tester_router.get("/dashboard")
def render_tester_dashboard(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
):
    recent_test_results = list_recent_test_results(database_session=database_session, limit=20)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="tester_dashboard.html",
        context={
            "request": request,
            "page_title": "Tester Dashboard",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
        },
    )


@tester_router.post("/rows/upsert")
def upsert_tester_row(
    test_result_partial_input: TestResultPartialInput,
    database_session: database_session_dependency,
):
    try:
        test_result = upsert_partial_test_result(
            database_session=database_session,
            test_result_partial_input=test_result_partial_input,
        )
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return {
        "message": "Row upserted.",
        "id": test_result.id,
        "key_1": test_result.key_1,
        "key_2": test_result.key_2,
        "key_3": test_result.key_3,
    }


@tester_router.post("/test_result/{id}/low_test/start")
def start_low_test(id: int, database_session: database_session_dependency):
    try:
        test_result = mark_low_test_start(database_session=database_session, test_result_id=id)
    except LookupError as exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exception),
        ) from exception
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return {
        "message": "low_test/start completed.",
        "id": test_result.id,
        "low_test_started_at": test_result.low_test_started_at,
    }


@tester_router.post("/test_result/{id}/low_test/end")
def end_low_test(id: int, database_session: database_session_dependency):
    try:
        test_result = mark_low_test_end(database_session=database_session, test_result_id=id)
    except LookupError as exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exception),
        ) from exception
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return {
        "message": "low_test/end completed.",
        "id": test_result.id,
        "low_test_ended_at": test_result.low_test_ended_at,
        "low_test_delta": test_result.low_test_delta,
    }


@tester_router.post("/test_result/{id}/high_test/start")
def start_high_test(id: int, database_session: database_session_dependency):
    try:
        test_result = mark_high_test_start(database_session=database_session, test_result_id=id)
    except LookupError as exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exception),
        ) from exception
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return {
        "message": "high_test/start completed.",
        "id": test_result.id,
        "high_test_started_at": test_result.high_test_started_at,
    }


@tester_router.post("/test_result/{id}/high_test/end")
def end_high_test(id: int, database_session: database_session_dependency):
    try:
        test_result = mark_high_test_end(database_session=database_session, test_result_id=id)
    except LookupError as exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exception),
        ) from exception
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return {
        "message": "high_test/end completed.",
        "id": test_result.id,
        "high_test_ended_at": test_result.high_test_ended_at,
        "high_test_delta": test_result.high_test_delta,
    }
