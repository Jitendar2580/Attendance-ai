from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Attendance, AttendanceStatus
from app.models.user import User, UserRole
from app.schemas.attendance import AttendanceCreate


def list_attendance(
    db: Session,
    offset: int = 0,
    limit: int = 20,
    status: AttendanceStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    team_id: int | None = None,
    user_id: int | None = None,
    user_name: str | None = None,
) -> list[Attendance]:
    query = (
        select(Attendance)
        .join(User, User.id == Attendance.user_id)
        .options(joinedload(Attendance.user))
        .order_by(Attendance.date.desc(), Attendance.created_at.desc())
    )
    if status:
        query = query.where(Attendance.status == status)
    if start_date:
        query = query.where(Attendance.date >= start_date)
    if end_date:
        query = query.where(Attendance.date <= end_date)
    if user_id is not None:
        query = query.where(Attendance.user_id == user_id)
    elif team_id is not None:
        query = query.where(User.team_id == team_id)
    if user_name:
        query = query.where(User.name.ilike(f"%{user_name}%"))
    query = query.offset(offset).limit(limit)
    return list(db.scalars(query))


def create_attendance(db: Session, payload: AttendanceCreate, actor: User) -> Attendance:
    existing = db.scalar(select(Attendance).where(and_(Attendance.user_id == payload.user_id, Attendance.date == payload.date)))
    if existing:
        raise ValueError("Attendance already exists for this user and date.")
    target_user = db.get(User, payload.user_id)
    if not target_user:
        raise ValueError("User not found.")
    if actor.role == UserRole.MANAGER and actor.team_id != target_user.team_id:
        raise ValueError("Managers can only mark attendance for their team.")
    if actor.role == UserRole.PLAYER and actor.id != target_user.id:
        raise ValueError("Players can only mark attendance for themselves.")
    attendance = Attendance(**payload.model_dump())
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


def today_presence(db: Session, team_id: int | None = None) -> tuple[int, int]:
    today = date.today()
    base_users_query = select(func.count(User.id)).where(User.role == UserRole.PLAYER)
    if team_id:
        base_users_query = base_users_query.where(User.team_id == team_id)
    total_players = db.scalar(base_users_query) or 0

    present_query = select(func.count(Attendance.id)).join(User, User.id == Attendance.user_id).where(Attendance.date == today)
    if team_id:
        present_query = present_query.where(User.team_id == team_id)
    present = db.scalar(present_query) or 0
    return present, max(total_players - present, 0)
