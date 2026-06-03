from datetime import date
from pathlib import Path
from uuid import uuid4
import shutil
import os

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.response_handlers import ResponseHandler
from app.models.attendance import AttendanceStatus
from app.models.user import User, UserRole
from app.schemas.attendance import AttendanceCreate
from app.services.attendance_service import create_attendance, list_attendance

router = APIRouter(prefix="/attendance", tags=["attendance"])
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
response_handler = ResponseHandler(templates)

# Constants
UPLOAD_DIR = Path("app/static/uploads")
VALID_IMAGE_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")


@router.get("")
def attendance_page(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: AttendanceStatus | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    user_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * page_size
    team_id = current_user.team_id if current_user.role == UserRole.MANAGER else None
    user_id = current_user.id if current_user.role == UserRole.PLAYER else None
    records = list_attendance(
        db,
        offset=offset,
        limit=page_size,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        team_id=team_id,
        user_id=user_id,
        user_name=user_name,
    )
    users_query = select(User).where(User.role == UserRole.PLAYER)
    if current_user.role == UserRole.MANAGER:
        users_query = users_query.where(User.team_id == current_user.team_id)
    users = list(db.scalars(users_query))

    return response_handler.template_response(
        request,
        "attendance/index.html",
        {
            "user": current_user,
            "records": records,
            "users": users,
            "statuses": list(AttendanceStatus),
            "status_filter": status_filter,
            "start_date": start_date,
            "end_date": end_date,
            "user_name": user_name,
            "is_player": current_user.role == UserRole.PLAYER,
        },
    )


@router.post("/create")
def create_attendance_action(
    user_id: int = Form(...),
    attendance_date: date = Form(...),
    status_value: AttendanceStatus = Form(...),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    payload = AttendanceCreate(user_id=user_id, date=attendance_date, status=status_value, notes=notes)
    try:
        create_attendance(db, payload, actor)
        return response_handler.redirect_success("Attendance saved successfully", "/attendance")
    except ValueError as exc:
        return response_handler.redirect_error(str(exc), "/attendance")


@router.post("/upload")
def upload_attendance(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PLAYER)),
):
    if not image.content_type.startswith("image/"):
        return response_handler.redirect_error("Please upload a valid image file.", "/dashboard")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(image.filename).suffix or ".jpg"
    filename = f"user_{current_user.id}_{date.today().isoformat()}_{uuid4().hex}{extension}"
    filepath = UPLOAD_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_path = f"/static/uploads/{filename}"
    payload = AttendanceCreate(
        user_id=current_user.id,
        date=date.today(),
        status=AttendanceStatus.TRAINING,
        notes="Camera attendance captured",
        image_path=image_path,
    )
    try:
        create_attendance(db, payload, current_user)
        return response_handler.redirect_success("Attendance recorded successfully", "/dashboard")
    except ValueError as exc:
        return response_handler.redirect_error(str(exc), "/dashboard")


@router.get("/export.csv")
def export_attendance_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export attendance records as CSV."""
    team_id = current_user.team_id if current_user.role == UserRole.MANAGER else None
    user_id = current_user.id if current_user.role == UserRole.PLAYER else None
    records = list_attendance(db, offset=0, limit=1000, team_id=team_id, user_id=user_id)
    
    lines = ["id,user,date,status,notes"]
    for record in records:
        notes = (record.notes or "").replace(",", " ")
        lines.append(f"{record.id},{record.user.name},{record.date},{record.status.value},{notes}")
    
    data = "\n".join(lines)
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance.csv"}
    )
