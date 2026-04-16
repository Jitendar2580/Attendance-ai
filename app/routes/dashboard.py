from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response_handlers import ResponseHandler
from app.models.user import User, UserRole
from app.services.ai_service import generate_insights
from app.services.dashboard_service import build_dashboard_metrics
from app.services.dashboard_helper import get_player_dashboard_metrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
response_handler = ResponseHandler(templates)


@router.get("")
def dashboard(
    request: Request,
    days: int = Query(default=14, ge=7, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard view for current user (admin, manager, or player)."""
    if current_user.role == UserRole.PLAYER:
        metrics = get_player_dashboard_metrics(db, current_user.id)
        return response_handler.template_response(
            request,
            "dashboard/player.html",
            {
                "user": current_user,
                "recent_logs": metrics["recent_logs"],
                "total_records": metrics["total_records"],
                "present_today": metrics["present_today"],
                "status_distribution": metrics["status_distribution"],
                "days": days,
            },
        )

    # Admin or Manager dashboard
    team_id = current_user.team_id if current_user.role == UserRole.MANAGER else None
    metrics, recent_logs, extras = build_dashboard_metrics(db, team_id=team_id)
    insights = generate_insights(db, days=days, team_id=team_id)
    
    return response_handler.template_response(
        request,
        "dashboard/index.html",
        {
            "user": current_user,
            "metrics": metrics,
            "recent_logs": recent_logs,
            "insights": insights,
            "days": days,
            "extras": extras,
        },
    )
