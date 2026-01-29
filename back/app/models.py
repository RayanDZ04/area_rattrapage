from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    service_tokens: Mapped[list["ServiceToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    applets: Mapped[list["Applet"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ServiceToken(Base):
    __tablename__ = "service_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(50), index=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="service_tokens")


class Applet(Base):
    __tablename__ = "applets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    action_service: Mapped[str] = mapped_column(String(50))
    action_choice: Mapped[str] = mapped_column(String(100))
    reaction_service: Mapped[str] = mapped_column(String(50))
    reaction_choice: Mapped[str] = mapped_column(String(100))
    action_config: Mapped[str] = mapped_column(Text, default="{}")
    reaction_config: Mapped[str] = mapped_column(Text, default="{}")
    last_action_marker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="applets")


class AppletLog(Base):
    __tablename__ = "applet_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    applet_id: Mapped[int] = mapped_column(Integer, ForeignKey("applets.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
