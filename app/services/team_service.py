from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team
from app.schemas.team import TeamCreate, TeamUpdate


def list_teams(db: Session) -> list[Team]:
    return list(db.scalars(select(Team).order_by(Team.name)))


def create_team(db: Session, payload: TeamCreate) -> Team:
    team = Team(name=payload.name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def update_team(db: Session, team: Team, payload: TeamUpdate) -> Team:
    team.name = payload.name
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def delete_team(db: Session, team: Team) -> None:
    db.delete(team)
    db.commit()
