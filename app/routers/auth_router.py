from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse


auth_router = APIRouter(tags=["auth"])


@auth_router.get("/")
def redirect_root_to_login():
    return RedirectResponse(url="/login", status_code=303)


@auth_router.get("/login")
def render_login_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "page_title": "Login"},
    )


@auth_router.post("/login")
def handle_login_submission(
    request: Request,
    user_name: str = Form(...),
    password: str = Form(...),
):
    _ = password
    if user_name.lower().startswith("admin"):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return RedirectResponse(url="/tester/dashboard", status_code=303)
