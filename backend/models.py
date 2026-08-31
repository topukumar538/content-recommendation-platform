from sqlalchemy import String, ForeignKey, Text, DateTime, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint, Index


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OTPCode(Base):
    __tablename__ = "otp_codes"
    id         : Mapped[int]  = mapped_column(primary_key=True)
    email      : Mapped[str]  = mapped_column(String, index=True)
    code       : Mapped[str]  = mapped_column(String)
    purpose    : Mapped[str]  = mapped_column(String)
    is_used    : Mapped[bool] = mapped_column(Boolean, default=False)
    attempts   : Mapped[int]  = mapped_column(Integer, default=0)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    feeds: Mapped[list["Feed"]] = relationship("Feed", back_populates="category")




class Feed(Base):
    __tablename__ = "feeds"
    id          : Mapped[int]      = mapped_column(primary_key=True)
    title       : Mapped[str]      = mapped_column(String)
    content     : Mapped[str]      = mapped_column(Text)
    category_id : Mapped[int]      = mapped_column(ForeignKey("categories.id"))
    author_id   : Mapped[int]      = mapped_column(ForeignKey("users.id"))
    created_at  : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    category    : Mapped["Category"] = relationship("Category", back_populates="feeds")
    author      : Mapped["User"]    = relationship("User")

    __table_args__ = (
        Index("ix_feeds_created_at", "created_at"),
    )




class UserInteraction(Base):
    __tablename__ = "user_interactions"
    id         : Mapped[int] = mapped_column(primary_key=True)
    user_id    : Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    feed_id    : Mapped[int] = mapped_column(ForeignKey("feeds.id"), index=True)
    action     : Mapped[str] = mapped_column(String)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "feed_id", "action", name="uq_user_feed_action"),
    )

class CategoryPreference(Base):
    __tablename__ = "category_preferences"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_user_category"),
    )

class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped["User"] = relationship("User")


