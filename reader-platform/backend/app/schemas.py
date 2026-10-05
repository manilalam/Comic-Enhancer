from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .models import ContentRating, ReadingDirection, SeriesFormat, SeriesStatus


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TagOut(ORM):
    name: str
    kind: str


class SeriesCard(ORM):
    id: int
    title: str
    slug: str
    format: SeriesFormat
    content_rating: ContentRating
    status: SeriesStatus
    cover_url: str | None
    tags: list[TagOut]


class ChapterSummary(ORM):
    number: int
    title: str
    published_at: datetime | None


class SeriesDetail(SeriesCard):
    description: str
    reading_direction: ReadingDirection
    creator_name: str
    chapters: list[ChapterSummary]


class PageOut(ORM):
    page_number: int
    image_url: str
    width: int
    height: int


class ChapterOut(BaseModel):
    series_slug: str
    series_title: str
    format: SeriesFormat
    reading_direction: ReadingDirection
    number: int
    title: str
    pages: list[PageOut]
    body_text: str | None
    prev_number: int | None
    next_number: int | None


class CharacterFactOut(ORM):
    text: str
    revealed_in_chapter: int


class CharacterCard(BaseModel):
    id: int
    name: str
    aliases: list[str]
    avatar_url: str | None
    first_appearance_chapter: int
    facts: list[CharacterFactOut]
