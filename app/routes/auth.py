from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response_handlers import ResponseHandler
from app.models.user import UserRole
from app.schemas.user import UserCreate
from app.services.auth_service import authenticate_user
from app.services.team_service import list_teams
from app.services.user_service import create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")
response_handler = ResponseHandler(templates)

ALLOWED_REGISTER_ROLES = [UserRole.MANAGER, UserRole.PLAYER]


@router.get("/login")
def login_page(request: Request):
    return response_handler.template_response("auth/login.html", request)


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, email=email, password=password)
    if not user:
        return response_handler.template_error(
            request,
            "auth/login.html",
            "Invalid email or password.",
        )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register")
def register_page(request: Request, db: Session = Depends(get_db)):
    return response_handler.template_response(
        "auth/register.html",
        request,
        {"teams": list_teams(db), "roles": ALLOWED_REGISTER_ROLES},
    )


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: UserRole = Form(...),
    team_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    def _get_register_page_context():
        return {
            "teams": list_teams(db),
            "roles": ALLOWED_REGISTER_ROLES,
        }

    if role == UserRole.ADMIN:
        return response_handler.template_error(
            request,
            "auth/register.html",
            "Registration for admin accounts is not allowed.",
            _get_register_page_context(),
        )

    if get_user_by_email(db, email):
        return response_handler.template_error(
            request,
            "auth/register.html",
            "Email already in use.",
            _get_register_page_context(),
        )

    team_id_value = int(team_id) if team_id else None
    payload = UserCreate(
        name=name,
        email=email,
        password=password,
        role=role,
        team_id=team_id_value,
    )
    user = create_user(db, payload)
    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
