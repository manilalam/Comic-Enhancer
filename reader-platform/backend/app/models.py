"""Database models for the MVP.

Spoiler safety is built into the schema: every character, alias and fact
records the chapter where readers first learn it, and reading progress keeps
the furthest chapter a reader has reached.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# ---------- Enums ----------

class UserRole(str, enum.Enum):
    reader = "reader"
    creator = "creator"
    admin = "admin"


class SeriesFormat(str, enum.Enum):
    webtoon = "webtoon"  # vertical scroll
    manga = "manga"      # page by page
    novel = "novel"      # text


class ReadingDirection(str, enum.Enum):
    ltr = "ltr"
    rtl = "rtl"


class ContentRating(str, enum.Enum):
    all_ages = "all_ages"
    teen = "teen"
    mature = "mature"


class SeriesStatus(str, enum.Enum):
    ongoing = "ongoing"
    completed = "completed"
    hiatus = "hiatus"


class ReportTarget(str, enum.Enum):
    series = "series"
    chapter = "chapter"
    comment = "comment"
    user = "user"


class CaseStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


def _enum(e: type[enum.Enum]) -> SAEnum:
    # Stored as plain strings so adding values later doesn't need a DB enum migration
    return SAEnum(e, native_enum=False, length=20)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------- Users ----------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))  # null for Google/OTP-only users
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.reader)
    is_adult: Mapped[bool] = mapped_column(default=False)      # age confirmed 18+
    show_mature: Mapped[bool] = mapped_column(default=False)   # opted in to mature content
    is_banned: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = _created()

    series: Mapped[list[Series]] = relationship(back_populates="creator")


# ---------- Catalog ----------

series_tags = Table(
    "series_tags",
    Base.metadata,
    Column("series_id", ForeignKey("series.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    kind: Mapped[str] = mapped_column(String(10), default="tag")  # "genre" or "tag"


class Series(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    format: Mapped[SeriesFormat] = mapped_column(_enum(SeriesFormat))
    reading_direction: Mapped[ReadingDirection] = mapped_column(
        _enum(ReadingDirection), default=ReadingDirection.ltr
    )
    content_rating: Mapped[ContentRating] = mapped_column(
        _enum(ContentRating), default=ContentRating.all_ages
    )
    status: Mapped[SeriesStatus] = mapped_column(_enum(SeriesStatus), default=SeriesStatus.ongoing)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    ownership_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_hidden: Mapped[bool] = mapped_column(default=False)  # set by moderation or takedown
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    creator: Mapped[User] = relationship(back_populates="series")
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="series", order_by="Chapter.number", cascade="all, delete-orphan"
    )
    characters: Mapped[list[Character]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )
    tags: Mapped[list[Tag]] = relationship(secondary=series_tags)


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("series_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200), default="")
    body_text: Mapped[str | None] = mapped_column(Text)  # novels only
    # None = draft. A future date = scheduled. Past date = live.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = _created()

    series: Mapped[Series] = relationship(back_populates="chapters")
    pages: Mapped[list[Page]] = relationship(
        back_populates="chapter", order_by="Page.page_number", cascade="all, delete-orphan"
    )


class Page(Base):
    """One image of a chapter. Long webtoon strips are sliced into several pages at upload."""
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("chapter_id", "page_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str] = mapped_column(String(500))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)

    chapter: Mapped[Chapter] = relationship(back_populates="pages")


# ---------- Spoiler-safe story context ----------

class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), index=True)
    # The name readers first know them by. A real name revealed later goes in aliases.
    name: Mapped[str] = mapped_column(String(100))
    # [{"name": "...", "revealed_in_chapter": 3}]; aliases can be spoilers too
    aliases: Mapped[list[dict]] = mapped_column(JSON, default=list)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    first_appearance_chapter: Mapped[int] = mapped_column(Integer)

    series: Mapped[Series] = relationship(back_populates="characters")
    facts: Mapped[list[CharacterFact]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )


class CharacterFact(Base):
    __tablename__ = "character_facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    revealed_in_chapter: Mapped[int] = mapped_column(Integer, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    character: Mapped[Character] = relationship(back_populates="facts")


# ---------- Reader state ----------

class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), primary_key=True)
    current_chapter: Mapped[int] = mapped_column(Integer)
    scroll_position: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0–1.0 within the chapter
    # Spoiler checks use the furthest chapter reached, so re-reading an old chapter
    # doesn't hide things the reader already knows
    furthest_chapter: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LibraryEntry(Base):
    """A followed series."""
    __tablename__ = "library_entries"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = _created()


class Bookmark(Base):
    __tablename__ = "bookmarks"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = _created()


# ---------- Social ----------

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    is_hidden: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = _created()


class PanelReaction(Base):
    __tablename__ = "panel_reactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Vertical position in the chapter, 0.0 = top, 1.0 = bottom. Works for any
    # screen size, and bucketing these values gives the reaction heatmap.
    position: Mapped[float] = mapped_column(Float)
    reaction: Mapped[str] = mapped_column(String(16))  # e.g. "wow", "lol", "sad", "fire"
    created_at: Mapped[datetime] = _created()


# ---------- Safety ----------

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_type: Mapped[ReportTarget] = mapped_column(_enum(ReportTarget))
    target_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(50))
    details: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[CaseStatus] = mapped_column(_enum(CaseStatus), default=CaseStatus.open, index=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _created()


class TakedownRequest(Base):
    """Copyright claims. Can be filed without an account."""
    __tablename__ = "takedown_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int | None] = mapped_column(ForeignKey("series.id", ondelete="SET NULL"))
    claimant_name: Mapped[str] = mapped_column(String(120))
    claimant_email: Mapped[str] = mapped_column(String(255))
    original_work: Mapped[str] = mapped_column(Text)  # what they say was copied
    details: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[CaseStatus] = mapped_column(_enum(CaseStatus), default=CaseStatus.open, index=True)
    created_at: Mapped[datetime] = _created()
