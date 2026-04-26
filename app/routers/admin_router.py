import os

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ROLE_ADMIN, ROLE_MASTER_ADMIN, ROLE_TESTER
from app.deps import current_role_name_dependency, database_session_dependency
from app.models import UserAccount
from app.schemas import TestResultReviewCompleteInput
from app.services.form_submission_service import (
    approve_submission,
    count_rows_by_submission_ids,
    list_submission_summaries_for_admin,
    list_submissions_for_admin,
    delete_submission_and_rows,
)
from app.services.test_result_service import (
    list_recent_test_results,
    mark_test_results_review_complete_by_ids,
    mark_test_results_review_pending_by_ids,
)
from app.services.dropdown_option_service import (
    add_dropdown_option_if_missing,
    delete_dropdown_option_if_exists,
    list_dropdown_options_for_field,
)


admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _admin_identity_context(database_session: Session, request: Request) -> dict:
    qc_mode_enabled = os.getenv("QC_MODE", "True").strip().lower() in {"1", "true", "yes", "on"}
    cookie_role_name = (request.cookies.get("role_name") or "").strip()
    if qc_mode_enabled and cookie_role_name == ROLE_MASTER_ADMIN:
        return {
            "current_admin_department_name": "",
            "current_admin_display_name": "마스터관리자",
            "current_admin_internal_title": "",
            "admin_greeting_text": "마스터관리자 님, 안녕하세요.",
        }

    normalized_phone_number = (request.cookies.get("phone_number") or "").strip()
    if not normalized_phone_number:
        return {
            "current_admin_department_name": "OO",
            "current_admin_display_name": "OOO",
            "current_admin_internal_title": "프로",
            "admin_greeting_text": "OO부서 OOO프로 님, 안녕하세요.",
        }

    user_account = database_session.scalar(
        select(UserAccount).where(UserAccount.phone_number == normalized_phone_number)
    )
    if user_account is None:
        return {
            "current_admin_department_name": "OO",
            "current_admin_display_name": "OOO",
            "current_admin_internal_title": "프로",
            "admin_greeting_text": "OO부서 OOO프로 님, 안녕하세요.",
        }

    department_name = (user_account.department_name or "").strip() or "OO"
    display_name = (user_account.display_name or "").strip() or "OOO"
    internal_title = (user_account.internal_title or "").strip() or "프로"
    return {
        "current_admin_department_name": department_name,
        "current_admin_display_name": display_name,
        "current_admin_internal_title": internal_title,
        "admin_greeting_text": f"{department_name}부서 {display_name}{internal_title} 님, 안녕하세요.",
    }


def _form_submissions_for_admin(database_session: Session) -> list[dict]:
    subs = list_submissions_for_admin(database_session=database_session, limit=200)
    if not subs:
        return []
    id_list = [s.submission_id for s in subs]
    counts = count_rows_by_submission_ids(database_session=database_session, submission_ids=id_list)
    return [
        {
            "submission": s,
            "row_count": int(counts.get(s.submission_id, 0)),
        }
        for s in subs
    ]


def _submission_summaries_for_admin(database_session: Session) -> list[dict]:
    return list_submission_summaries_for_admin(database_session=database_session, limit=200)


def _tester_accounts_for_admin(database_session: Session) -> list[UserAccount]:
    return list(
        database_session.scalars(
            select(UserAccount)
            .where(UserAccount.role_name == "tester")
            .order_by(UserAccount.created_at.desc())
        )
    )


def _admin_accounts_for_admin(database_session: Session) -> list[UserAccount]:
    return list(
        database_session.scalars(
            select(UserAccount)
            .where(UserAccount.role_name == ROLE_ADMIN)
            .order_by(UserAccount.created_at.desc())
        )
    )


@admin_router.get("")
def render_admin_dashboard(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
):
    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    pending_tester_join_requests = _tester_accounts_for_admin(database_session)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "page_title": "ELT 시험 데이터 트래킹 시스템",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
            **_admin_identity_context(database_session=database_session, request=request),
            "admin_create_error_message": "",
            "admin_create_success_message": "",
            "tester_create_error_message": "",
            "tester_create_success_message": "",
            "form_submissions": _form_submissions_for_admin(database_session),
            "submission_summaries": _submission_summaries_for_admin(database_session),
            "pending_tester_join_requests": pending_tester_join_requests,
            "admin_accounts_for_management": _admin_accounts_for_admin(database_session),
        },
    )


@admin_router.post("/create_admin")
def create_admin_user_account(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
    department_name: str = Form(...),
    display_name: str = Form(...),
    internal_title: str = Form(...),
    phone_number: str = Form(...),
    password: str = Form(...),
):
    normalized_department_name = department_name.strip()
    normalized_display_name = display_name.strip()
    normalized_internal_title = internal_title.strip()
    normalized_phone_number = phone_number.strip()
    normalized_password = password.strip()

    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    templates = request.app.state.templates

    if (
        not normalized_department_name
        or not normalized_display_name
        or not normalized_internal_title
        or not normalized_phone_number
        or not normalized_password
    ):
        pending_tester_join_requests = _tester_accounts_for_admin(database_session)
        return templates.TemplateResponse(
            request=request,
            name="admin_dashboard.html",
            context={
                "request": request,
                "page_title": "ELT 시험 데이터 트래킹 시스템",
                "recent_test_results": recent_test_results,
                "current_role_name": current_role_name,
                "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
                **_admin_identity_context(database_session=database_session, request=request),
                "admin_create_error_message": "모든 항목을 입력해 주세요.",
                "admin_create_success_message": "",
                "tester_create_error_message": "",
                "tester_create_success_message": "",
                "form_submissions": _form_submissions_for_admin(database_session),
                "submission_summaries": _submission_summaries_for_admin(database_session),
                "pending_tester_join_requests": pending_tester_join_requests,
            },
            status_code=400,
        )

    existing_user_account = database_session.scalar(
        select(UserAccount).where(UserAccount.phone_number == normalized_phone_number)
    )
    if existing_user_account is not None:
        pending_tester_join_requests = _tester_accounts_for_admin(database_session)
        return templates.TemplateResponse(
            request=request,
            name="admin_dashboard.html",
            context={
                "request": request,
                "page_title": "ELT 시험 데이터 트래킹 시스템",
                "recent_test_results": recent_test_results,
                "current_role_name": current_role_name,
                "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
                **_admin_identity_context(database_session=database_session, request=request),
                "admin_create_error_message": "이미 등록된 전화번호입니다.",
                "admin_create_success_message": "",
                "tester_create_error_message": "",
                "tester_create_success_message": "",
                "form_submissions": _form_submissions_for_admin(database_session),
                "submission_summaries": _submission_summaries_for_admin(database_session),
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
        internal_title=normalized_internal_title,
        is_approved=True,
    )
    database_session.add(new_admin_account)
    database_session.commit()

    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    pending_tester_join_requests = _tester_accounts_for_admin(database_session)
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "page_title": "ELT 시험 데이터 트래킹 시스템",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
            **_admin_identity_context(database_session=database_session, request=request),
            "admin_create_error_message": "",
            "admin_create_success_message": "Admin 계정이 생성되었습니다.",
            "tester_create_error_message": "",
            "tester_create_success_message": "",
            "form_submissions": _form_submissions_for_admin(database_session),
            "submission_summaries": _submission_summaries_for_admin(database_session),
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
    pending_tester_join_requests = _tester_accounts_for_admin(database_session)
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
                "page_title": "ELT 시험 데이터 트래킹 시스템",
                "recent_test_results": recent_test_results,
                "current_role_name": current_role_name,
                "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
                **_admin_identity_context(database_session=database_session, request=request),
                "admin_create_error_message": "",
                "admin_create_success_message": "",
                "tester_create_error_message": "모든 항목을 입력해 주세요.",
                "tester_create_success_message": "",
                "form_submissions": _form_submissions_for_admin(database_session),
                "submission_summaries": _submission_summaries_for_admin(database_session),
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
                "page_title": "ELT 시험 데이터 트래킹 시스템",
                "recent_test_results": recent_test_results,
                "current_role_name": current_role_name,
                "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
                **_admin_identity_context(database_session=database_session, request=request),
                "admin_create_error_message": "",
                "admin_create_success_message": "",
                "tester_create_error_message": "이미 등록된 전화번호입니다.",
                "tester_create_success_message": "",
                "form_submissions": _form_submissions_for_admin(database_session),
                "submission_summaries": _submission_summaries_for_admin(database_session),
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
    pending_tester_join_requests = _tester_accounts_for_admin(database_session)
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "page_title": "ELT 시험 데이터 트래킹 시스템",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
            **_admin_identity_context(database_session=database_session, request=request),
            "admin_create_error_message": "",
            "admin_create_success_message": "",
            "tester_create_error_message": "",
            "tester_create_success_message": "Tester 계정이 생성되었습니다.",
            "form_submissions": _form_submissions_for_admin(database_session),
            "submission_summaries": _submission_summaries_for_admin(database_session),
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
    pending_tester_join_requests = _tester_accounts_for_admin(database_session)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "page_title": "ELT 시험 데이터 트래킹 시스템",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
            **_admin_identity_context(database_session=database_session, request=request),
            "admin_create_error_message": "",
            "admin_create_success_message": "업체 등록이 승인되었습니다.",
            "tester_create_error_message": "",
            "tester_create_success_message": "",
            "form_submissions": _form_submissions_for_admin(database_session),
            "submission_summaries": _submission_summaries_for_admin(database_session),
            "pending_tester_join_requests": pending_tester_join_requests,
        },
    )


@admin_router.post("/delete_tester_join")
def delete_tester_join_request(
    request: Request,
    database_session: database_session_dependency,
    current_role_name: current_role_name_dependency,
    user_account_id: int = Form(...),
):
    user_account = database_session.get(UserAccount, user_account_id)
    if user_account is not None and user_account.role_name == "tester":
        database_session.delete(user_account)
        database_session.commit()

    recent_test_results = list_recent_test_results(database_session=database_session, limit=50)
    pending_tester_join_requests = _tester_accounts_for_admin(database_session)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "page_title": "ELT 시험 데이터 트래킹 시스템",
            "recent_test_results": recent_test_results,
            "current_role_name": current_role_name,
            "can_edit_all_data": current_role_name == ROLE_MASTER_ADMIN,
            **_admin_identity_context(database_session=database_session, request=request),
            "admin_create_error_message": "",
            "admin_create_success_message": "업체 회원이 삭제되었습니다.",
            "tester_create_error_message": "",
            "tester_create_success_message": "",
            "form_submissions": _form_submissions_for_admin(database_session),
            "submission_summaries": _submission_summaries_for_admin(database_session),
            "pending_tester_join_requests": pending_tester_join_requests,
        },
    )


@admin_router.post("/delete_admin_user")
def delete_admin_user_account(
    request: Request,
    database_session: database_session_dependency,
    user_account_id: int = Form(...),
):
    target_admin_user_account = database_session.get(UserAccount, user_account_id)
    if target_admin_user_account is not None and target_admin_user_account.role_name == ROLE_ADMIN:
        current_phone_number = (request.cookies.get("phone_number") or "").strip()
        target_phone_number = (target_admin_user_account.phone_number or "").strip()
        if current_phone_number and target_phone_number and current_phone_number == target_phone_number:
            return RedirectResponse(url="/admin", status_code=303)
        database_session.delete(target_admin_user_account)
        database_session.commit()
    return RedirectResponse(url="/admin", status_code=303)


@admin_router.post("/submission/approve")
def approve_submission_by_submission_id(
    database_session: database_session_dependency,
    form_submission_id: str = Form(""),
):
    target_id = (form_submission_id or "").strip()
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="form_submission_id is required",
        )
    try:
        approve_submission(
            database_session=database_session,
            submission_id=target_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return RedirectResponse(url="/admin", status_code=303)


@admin_router.post("/submission/delete")
def delete_submission_by_form_submission_id(
    database_session: database_session_dependency,
    form_submission_id: str = Form(""),
):
    target_id = (form_submission_id or "").strip()
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="form_submission_id is required",
        )
    try:
        delete_submission_and_rows(database_session=database_session, submission_id=target_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RedirectResponse(url="/admin", status_code=303)




 




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


@admin_router.post("/rows/review_pending")
def mark_admin_rows_review_pending(
    test_result_review_complete_input: TestResultReviewCompleteInput,
    database_session: database_session_dependency,
):
    updated_count = mark_test_results_review_pending_by_ids(
        database_session=database_session,
        row_ids=test_result_review_complete_input.row_ids,
    )
    return {"message": "Rows review-pending.", "updated_count": updated_count}


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
