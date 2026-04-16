from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.response_handlers import ResponseHandler
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services.team_service import list_teams
from app.services.user_service import create_user, get_user_by_email, list_users

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="app/templates")
response_handler = ResponseHandler(templates)


@router.get("")
def users_page(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    offset = (page - 1) * page_size
    users = list_users(db, offset=offset, limit=page_size)
    teams = list_teams(db)
    return response_handler.template_response(
        request,
        "users/index.html",
        {
            "user": current_user,
            "users": users,
            "teams": teams,
            "roles": list(UserRole),
        },
    )


@router.post("/create")
def create_user_action(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: UserRole = Form(...),
    team_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    if current_user.role == UserRole.MANAGER and role == UserRole.ADMIN:
        return response_handler.redirect_error("Managers cannot create admins", "/users")
    if get_user_by_email(db, email):
        return response_handler.redirect_error("Email already in use", "/users")
    
    payload = UserCreate(name=name, email=email, password=password, role=role, team_id=team_id)
    create_user(db, payload)
    return response_handler.redirect_success("User created successfully", "/users")
