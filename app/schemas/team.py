from pydantic import BaseModel, ConfigDict, Field


class TeamBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class TeamOut(TeamBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
