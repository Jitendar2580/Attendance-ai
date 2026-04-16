"""Dashboard service for building metrics and retrieving dashboard data."""
from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance


def get_player_dashboard_metrics(db: Session, user_id: int):
    """Get dashboard metrics for a player user."""
    recent_logs = db.execute(
        select(Attendance)
        .where(Attendance.user_id == user_id)
        .order_by(Attendance.date.desc())
        .limit(20)
    ).scalars().all()
    
    total_records = db.scalar(
        select(func.count(Attendance.id)).where(Attendance.user_id == user_id)
    ) or 0
    
    present_today = db.scalar(
        select(func.count(Attendance.id))
        .where(Attendance.user_id == user_id)
        .where(Attendance.date == date.today())
    ) or 0
    
    status_rows = db.execute(
        select(Attendance.status, func.count(Attendance.id))
        .where(Attendance.user_id == user_id)
        .group_by(Attendance.status)
    ).all()
    status_distribution = {row[0].value: row[1] for row in status_rows}
    
    return {
        "recent_logs": recent_logs,
        "total_records": total_records,
        "present_today": present_today,
        "status_distribution": status_distribution,
    }
