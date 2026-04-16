from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.response_handlers import ResponseHandler
from app.models.team import Team
from app.models.user import User, UserRole
from app.schemas.team import TeamCreate
from app.services.team_service import create_team, delete_team, list_teams

router = APIRouter(prefix="/teams", tags=["teams"])
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
response_handler = ResponseHandler(templates)


@router.get("")
def teams_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return response_handler.template_response(
        request,
        "teams/index.html",
        {"user": current_user, "teams": list_teams(db)},
    )


@router.post("/create")
def create_team_action(
    name: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    payload = TeamCreate(name=name)
    create_team(db, payload)
    return response_handler.redirect_success("Team created successfully", "/teams")


@router.post("/{team_id}/delete")
def delete_team_action(
    team_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")
    delete_team(db, team)
    return response_handler.redirect_success("Team deleted", "/teams")
