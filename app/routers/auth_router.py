from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import ensure_active_user_limit


auth_router = APIRouter(tags=["auth"])


@auth_router.get("/")
def redirect_root_to_login():
    return RedirectResponse(url="/login", status_code=303)


@auth_router.get("/login")
def render_login_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "page_title": "Login"},
    )


@auth_router.post("/login")
def handle_login_submission(
    request: Request,
    user_name: str = Form(...),
    password: str = Form(...),
):
    _ = password
    ensure_active_user_limit(user_name=user_name)
    if user_name.lower().startswith("admin"):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return RedirectResponse(url="/tester/dashboard", status_code=303)
