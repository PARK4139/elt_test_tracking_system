from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.auth import ROLE_ADMIN, ROLE_MASTER_ADMIN, ROLE_TESTER
from app.deps import current_role_name_dependency, database_session_dependency
from app.models import UserAccount
from app.schemas import TestResultReviewCompleteInput
from app.services.test_result_service import (
    list_recent_test_results,
    mark_test_results_review_complete_by_ids,
)
from app.services.dropdown_option_service import (
    add_dropdown_option_if_missing,
    delete_dropdown_option_if_exists,
    list_dropdown_options_for_field,
)


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("")
def render_admin_dashboard(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
):
    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    pending_tester_join_requests = list(
        database_session.scalars(
            select(UserAccount)
            .where(UserAccount.role_name == "tester", UserAccount.is_approved == False)  # noqa: E712
            .order_by(UserAccount.created_at.asc())
        )
    )
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
            "admin_create_error_message": "",
            "admin_create_success_message": "",
            "tester_create_error_message": "",
            "tester_create_success_message": "",
            "pending_tester_join_requests": pending_tester_join_requests,
        },
    )


@admin_router.post("/create_admin")
def create_admin_user_account(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
    department_name: str = Form(...),
    display_name: str = Form(...),
    phone_number: str = Form(...),
    password: str = Form(...),
):
    normalized_department_name = department_name.strip()
    normalized_display_name = display_name.strip()
    normalized_phone_number = phone_number.strip()
    normalized_password = password.strip()

    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    templates = request.app.state.templates

    if (
        not normalized_department_name
        or not normalized_display_name
        or not normalized_phone_number
        or not normalized_password
    ):
        pending_tester_join_requests = list(
            database_session.scalars(
                select(UserAccount)
                .where(UserAccount.role_name == "tester", UserAccount.is_approved == False)  # noqa: E712
                .order_by(UserAccount.created_at.asc())
            )
        )
        return templates.TemplateResponse(
            request=request,
            name="admin_dashboard.html",
            context={
                "request": request,
                "page_title": "Admin Dashboard",
                "recent_test_results": recent_test_results,
                "current_role_name": current_role_name,
                "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
                "admin_create_error_message": "모든 항목을 입력해 주세요.",
                "admin_create_success_message": "",
                "tester_create_error_message": "",
                "tester_create_success_message": "",
                "pending_tester_join_requests": pending_tester_join_requests,
            },
            status_code=400,
        )

    existing_user_account = database_session.scalar(
        select(UserAccount).where(UserAccount.phone_number == normalized_phone_number)
    )
    if existing_user_account is not None:
        pending_tester_join_requests = list(
            database_session.scalars(
                select(UserAccount)
                .where(UserAccount.role_name == "tester", UserAccount.is_approved == False)  # noqa: E712
                .order_by(UserAccount.created_at.asc())
            )
        )
        return templates.TemplateResponse(
            request=request,
            name="admin_dashboard.html",
            context={
                "request": request,
                "page_title": "Admin Dashboard",
                "recent_test_results": recent_test_results,
                "current_role_name": current_role_name,
                "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
                "admin_create_error_message": "이미 등록된 전화번호입니다.",
                "admin_create_success_message": "",
                "tester_create_error_message": "",
                "tester_create_success_message": "",
                "pending_tester_join_requests": pending_tester_join_requests,
            },
            status_code=400,
        )

    new_admin_account = UserAccount(
        user_name=normalized_phone_number,
        password_hash=normalized_password,
        role_name=ROLE_ADMIN,
        display_name=normalized_display_name,
        phone_number=normalized_phone_number,
        company_name=None,
        department_name=normalized_department_name,
        is_approved=True,
    )
    database_session.add(new_admin_account)
    database_session.commit()

    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    pending_tester_join_requests = list(
        database_session.scalars(
            select(UserAccount)
            .where(UserAccount.role_name == "tester", UserAccount.is_approved == False)  # noqa: E712
            .order_by(UserAccount.created_at.asc())
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "page_title": "Admin Dashboard",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
            "admin_create_error_message": "",
            "admin_create_success_message": "Admin 계정이 생성되었습니다.",
            "tester_create_error_message": "",
            "tester_create_success_message": "",
            "pending_tester_join_requests": pending_tester_join_requests,
        },
    )


@admin_router.post("/create_tester")
def create_tester_user_account(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
    company_name: str = Form(...),
    display_name: str = Form(...),
    phone_number: str = Form(...),
    password: str = Form(...),
):
    normalized_company_name = company_name.strip()
    normalized_display_name = display_name.strip()
    normalized_phone_number = phone_number.strip()
    normalized_password = password.strip()

    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    pending_tester_join_requests = list(
        database_session.scalars(
            select(UserAccount)
            .where(UserAccount.role_name == "tester", UserAccount.is_approved == False)  # noqa: E712
            .order_by(UserAccount.created_at.asc())
        )
    )
    templates = request.app.state.templates

    if (
        not normalized_company_name
        or not normalized_display_name
        or not normalized_phone_number
        or not normalized_password
    ):
        return templates.TemplateResponse(
            request=request,
            name="admin_dashboard.html",
            context={
                "request": request,
                "page_title": "Admin Dashboard",
                "recent_test_results": recent_test_results,
                "current_role_name": current_role_name,
                "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
                "admin_create_error_message": "",
                "admin_create_success_message": "",
                "tester_create_error_message": "모든 항목을 입력해 주세요.",
                "tester_create_success_message": "",
                "pending_tester_join_requests": pending_tester_join_requests,
            },
            status_code=400,
        )

    existing_user_account = database_session.scalar(
        select(UserAccount).where(UserAccount.phone_number == normalized_phone_number)
    )
    if existing_user_account is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin_dashboard.html",
            context={
                "request": request,
                "page_title": "Admin Dashboard",
                "recent_test_results": recent_test_results,
                "current_role_name": current_role_name,
                "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
                "admin_create_error_message": "",
                "admin_create_success_message": "",
                "tester_create_error_message": "이미 등록된 전화번호입니다.",
                "tester_create_success_message": "",
                "pending_tester_join_requests": pending_tester_join_requests,
            },
            status_code=400,
        )

    new_tester_account = UserAccount(
        user_name=normalized_phone_number,
        password_hash=normalized_password,
        role_name=ROLE_TESTER,
        display_name=normalized_display_name,
        phone_number=normalized_phone_number,
        company_name=normalized_company_name,
        department_name=None,
        is_approved=True,
    )
    database_session.add(new_tester_account)
    database_session.commit()

    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    pending_tester_join_requests = list(
        database_session.scalars(
            select(UserAccount)
            .where(UserAccount.role_name == "tester", UserAccount.is_approved == False)  # noqa: E712
            .order_by(UserAccount.created_at.asc())
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "page_title": "Admin Dashboard",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
            "admin_create_error_message": "",
            "admin_create_success_message": "",
            "tester_create_error_message": "",
            "tester_create_success_message": "Tester 계정이 생성되었습니다.",
            "pending_tester_join_requests": pending_tester_join_requests,
        },
    )


@admin_router.post("/approve_tester_join")
def approve_tester_join_request(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
    user_account_id: int = Form(...),
):
    user_account = database_session.get(UserAccount, user_account_id)
    if user_account is not None and user_account.role_name == "tester":
        user_account.is_approved = True
        database_session.commit()

    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    pending_tester_join_requests = list(
        database_session.scalars(
            select(UserAccount)
            .where(UserAccount.role_name == "tester", UserAccount.is_approved == False)  # noqa: E712
            .order_by(UserAccount.created_at.asc())
        )
    )
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
            "admin_create_error_message": "",
            "admin_create_success_message": "Tester join 요청이 수락되었습니다.",
            "tester_create_error_message": "",
            "tester_create_success_message": "",
            "pending_tester_join_requests": pending_tester_join_requests,
        },
    )


@admin_router.post("/rows/review_complete")
def mark_admin_rows_review_complete(
    test_result_review_complete_input: TestResultReviewCompleteInput,
    database_session: database_session_dependency,
):
    updated_count = mark_test_results_review_complete_by_ids(
        database_session=database_session,
        row_ids=test_result_review_complete_input.row_ids,
    )
    return {"message": "Rows review-completed.", "updated_count": updated_count}


@admin_router.post("/dropdown_options/add")
def add_admin_dropdown_option(
    database_session: database_session_dependency,
    field_name: str = Form(...),
    option_value: str = Form(...),
):
    try:
        add_dropdown_option_if_missing(
            database_session=database_session,
            field_name=field_name,
            option_value=option_value,
        )
    except ValueError:
        return RedirectResponse(url="/admin", status_code=303)
    return RedirectResponse(url="/admin", status_code=303)


@admin_router.post("/dropdown_options/delete")
def delete_admin_dropdown_option(
    database_session: database_session_dependency,
    field_name: str = Form(...),
    option_value: str = Form(...),
):
    try:
        delete_dropdown_option_if_exists(
            database_session=database_session,
            field_name=field_name,
            option_value=option_value,
        )
    except ValueError:
        return RedirectResponse(url="/admin", status_code=303)
    return RedirectResponse(url="/admin", status_code=303)


@admin_router.get("/dropdown_options/{field_name}")
def list_admin_dropdown_options_by_field(
    field_name: str,
    database_session: database_session_dependency,
):
    try:
        option_values = list_dropdown_options_for_field(
            database_session=database_session,
            field_name=field_name,
        )
    except ValueError:
        option_values = []
    return {"field_name": field_name, "option_values": option_values}
