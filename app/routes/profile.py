from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response_handlers import ResponseHandler
from app.models.user import User
from app.schemas.user import UserUpdate
from app.services.user_service import get_user_by_email, update_user

router = APIRouter(prefix="/profile", tags=["profile"])
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
response_handler = ResponseHandler(templates)


@router.get("")
def profile_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    team_name = current_user.team.name if current_user.team else None
    return response_handler.template_response(
        request,
        "profile/index.html",
        {"user": current_user, "team_name": team_name},
    )


@router.post("")
def update_profile(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = get_user_by_email(db, email)
    if existing and existing.id != current_user.id:
        return response_handler.template_error(
            request,
            "profile/index.html",
            "Email is already in use.",
            {"user": current_user, "team_name": current_user.team.name if current_user.team else None},
        )

    payload = UserUpdate(name=name, email=email, password=password)
    update_user(db, current_user, payload)
    return RedirectResponse(
        url="/profile?msg=Profile%20updated%20successfully&type=success",
        status_code=status.HTTP_303_SEE_OTHER,
    )
