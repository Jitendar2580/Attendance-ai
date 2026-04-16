from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    total_users: int
    present_today: int
    absent_today: int
    status_distribution: dict[str, int]
