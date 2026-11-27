from pydantic import BaseModel, Field

from src.constants.workflow import Role


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=1, max_length=128)


class Identity(BaseModel):
    email: str
    role: Role


class Token(Identity):
    access_token: str
