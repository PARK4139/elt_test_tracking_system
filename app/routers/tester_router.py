from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.deps import current_role_name_dependency
from app.deps import database_session_dependency
from app.schemas import TestResultDeleteInput, TestResultPartialInput, TestResultSaveAllInput
from app.models import UserAccount
from app.services.test_result_service import (
    list_unreviewed_test_results,
    mark_high_test_end,
    mark_high_test_start,
    mark_low_test_end,
    mark_low_test_start,
    delete_test_results_by_ids,
    save_all_test_results_atomically,
    upsert_partial_test_result,
)
from app.services.dropdown_option_service import list_dropdown_options_map

tester_router = APIRouter(prefix="/tester", tags=["tester"])


def _get_current_display_name(request: Request, database_session) -> str:
    phone_number = (request.cookies.get("phone_number") or "").strip()
    if not phone_number:
        return ""
    user_account = database_session.scalar(
        select(UserAccount).where(UserAccount.phone_number == phone_number)
    )
    if user_account is None:
        return ""
    return (user_account.display_name or "").strip()


@tester_router.get("")
def render_tester_dashboard(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
):
    recent_test_results = list_unreviewed_test_results(database_session=database_session)
    dropdown_options_map = list_dropdown_options_map(database_session=database_session)
    current_display_name = _get_current_display_name(
        request=request,
        database_session=database_session,
    )
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="tester_dashboard.html",
        context={
            "request": request,
            "page_title": "Tester Dashboard",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "current_display_name": current_display_name,
            "dropdown_options_map": dropdown_options_map,
        },
    )


@tester_router.post("/rows/upsert")
def upsert_tester_row(
    request: Request,
    test_result_partial_input: TestResultPartialInput,
    database_session: database_session_dependency,
):
    current_display_name = _get_current_display_name(
        request=request,
        database_session=database_session,
    )
    if current_display_name:
        test_result_partial_input.data_writer_name = current_display_name

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
        "submission_id": test_result.submission_id,
        "data_writer_name": test_result.data_writer_name,
        "key_1": test_result.key_1,
        "key_2": test_result.key_2,
        "key_3": test_result.key_3,
        "created_at": test_result.created_at,
        "updated_at": test_result.updated_at,
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


@tester_router.post("/rows/delete")
def delete_tester_rows(
    test_result_delete_input: TestResultDeleteInput,
    database_session: database_session_dependency,
):
    deleted_count = delete_test_results_by_ids(
        database_session=database_session,
        row_ids=test_result_delete_input.row_ids,
    )
    return {"message": "Rows deleted.", "deleted_count": deleted_count}


@tester_router.post("/rows/save_all")
def save_all_tester_rows(
    request: Request,
    test_result_save_all_input: TestResultSaveAllInput,
    database_session: database_session_dependency,
):
    current_display_name = _get_current_display_name(
        request=request,
        database_session=database_session,
    )
    if current_display_name:
        for row in test_result_save_all_input.rows:
            row.data_writer_name = current_display_name

    try:
        save_all_test_results_atomically(
            database_session=database_session,
            rows=test_result_save_all_input.rows,
            delete_row_ids=test_result_save_all_input.delete_row_ids,
        )
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return {"message": "All rows saved atomically."}
