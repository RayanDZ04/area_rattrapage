from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None


class AppletCreate(BaseModel):
    name: str = Field(min_length=1)
    action_service: str = Field(min_length=1)
    action_choice: str = Field(min_length=1)
    reaction_service: str = Field(min_length=1)
    reaction_choice: str = Field(min_length=1)
    action_config: dict = Field(default_factory=dict)
    reaction_config: dict = Field(default_factory=dict)


class AppletOut(BaseModel):
    id: int
    name: str
    action_service: str
    action_choice: str
    reaction_service: str
    reaction_choice: str
    action_config: dict
    reaction_config: dict
    created_at: datetime

    class Config:
        from_attributes = True


class AppletLogOut(BaseModel):
    id: int
    applet_id: int
    status: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
