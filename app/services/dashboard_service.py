from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.user import User, UserRole
from app.schemas.dashboard import DashboardMetrics
from app.services.attendance_service import today_presence


def build_dashboard_metrics(db: Session, team_id: int | None = None) -> tuple[DashboardMetrics, list[Attendance], dict]:
    total_users_query = select(func.count(User.id)).where(User.role == UserRole.PLAYER)
    status_distribution_query = (
        select(Attendance.status, func.count(Attendance.id))
        .join(User, User.id == Attendance.user_id)
        .where(Attendance.date == date.today())
        .group_by(Attendance.status)
    )
    recent_logs_query = (
        select(Attendance)
        .join(User, User.id == Attendance.user_id)
        .where(Attendance.date == date.today())
        .order_by(Attendance.created_at.desc())
    )

    if team_id:
        total_users_query = total_users_query.where(User.team_id == team_id)
        status_distribution_query = status_distribution_query.where(User.team_id == team_id)
        recent_logs_query = recent_logs_query.where(User.team_id == team_id)

    total_users = db.scalar(total_users_query) or 0
    present_today, absent_today = today_presence(db, team_id=team_id)
    distribution_rows = db.execute(status_distribution_query).all()
    status_distribution = {row[0].value: row[1] for row in distribution_rows}
    recent_logs = list(db.scalars(recent_logs_query.limit(10)))

    # Last 14 days attendance trend for line chart.
    since = date.today() - timedelta(days=13)
    trend_query = (
        select(Attendance.date, func.count(Attendance.id))
        .join(User, User.id == Attendance.user_id)
        .where(Attendance.date >= since)
        .group_by(Attendance.date)
        .order_by(Attendance.date.asc())
    )
    if team_id:
        trend_query = trend_query.where(User.team_id == team_id)
    trend_rows = db.execute(trend_query).all()
    trend_map = {row[0]: row[1] for row in trend_rows}
    trend_labels = []
    trend_values = []
    for idx in range(14):
        current = since + timedelta(days=idx)
        trend_labels.append(current.strftime("%d %b"))
        trend_values.append(trend_map.get(current, 0))

    # At-risk players: more frequent leave/hospital in recent period.
    risk_since = date.today() - timedelta(days=30)
    at_risk_query = (
        select(User.name, func.count(Attendance.id).label("misses"))
        .join(Attendance, Attendance.user_id == User.id)
        .where(Attendance.date >= risk_since)
        .where(Attendance.status.in_(["leave", "hospital"]))
        .group_by(User.id, User.name)
        .order_by(func.count(Attendance.id).desc())
        .limit(5)
    )
    if team_id:
        at_risk_query = at_risk_query.where(User.team_id == team_id)
    at_risk_players = [{"name": row[0], "misses": row[1]} for row in db.execute(at_risk_query).all()]
    compliance_rate = round((present_today / total_users) * 100, 1) if total_users else 0.0
    alert_level = "healthy"
    if compliance_rate < 55:
        alert_level = "critical"
    elif compliance_rate < 75:
        alert_level = "warning"

    top_status = None
    if status_distribution:
        top_status = max(status_distribution, key=status_distribution.get)

    return (
        DashboardMetrics(
            total_users=total_users,
            present_today=present_today,
            absent_today=absent_today,
            status_distribution=status_distribution,
        ),
        recent_logs,
        {
            "trend_labels": trend_labels,
            "trend_values": trend_values,
            "at_risk_players": at_risk_players,
            "compliance_rate": compliance_rate,
            "alert_level": alert_level,
            "top_status": top_status,
        },
    )
