from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..db import get_db
from ..models import (
    Chapter,
    Character,
    CharacterFact,
    ContentRating,
    Series,
    SeriesFormat,
)

router = APIRouter(prefix="/series", tags=["series"])


def _is_live():
    """Chapters that are published and whose release time has passed."""
    now = datetime.now(timezone.utc)
    return and_(Chapter.published_at.is_not(None), Chapter.published_at <= now)


def _get_visible_series(db: Session, slug: str) -> Series:
    series = db.scalar(
        select(Series)
        .options(selectinload(Series.tags), selectinload(Series.creator))
        .where(Series.slug == slug, Series.is_hidden.is_(False))
    )
    # Mature series stay hidden until auth (step 2) can check age and opt-in
    if series is None or series.content_rating == ContentRating.mature:
        raise HTTPException(status_code=404, detail="Series not found")
    return series


@router.get("", response_model=list[schemas.SeriesCard])
def list_series(
    format_: SeriesFormat | None = Query(None, alias="format"),
    q: str | None = Query(None, max_length=100, description="Search by title"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Series)
        .options(selectinload(Series.tags))
        .where(Series.is_hidden.is_(False), Series.content_rating != ContentRating.mature)
        .order_by(Series.updated_at.desc())
    )
    if format_:
        stmt = stmt.where(Series.format == format_)
    if q:
        stmt = stmt.where(Series.title.ilike(f"%{q}%"))
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{slug}", response_model=schemas.SeriesDetail)
def get_series(slug: str, db: Session = Depends(get_db)):
    series = _get_visible_series(db, slug)
    chapters = db.scalars(
        select(Chapter).where(Chapter.series_id == series.id, _is_live()).order_by(Chapter.number)
    ).all()
    return schemas.SeriesDetail(
        id=series.id,
        title=series.title,
        slug=series.slug,
        format=series.format,
        content_rating=series.content_rating,
        status=series.status,
        cover_url=series.cover_url,
        tags=[schemas.TagOut.model_validate(t) for t in series.tags],
        description=series.description,
        reading_direction=series.reading_direction,
        creator_name=series.creator.display_name,
        chapters=[schemas.ChapterSummary.model_validate(c) for c in chapters],
    )


@router.get("/{slug}/chapters/{number}", response_model=schemas.ChapterOut)
def get_chapter(slug: str, number: int, db: Session = Depends(get_db)):
    series = _get_visible_series(db, slug)
    chapter = db.scalar(
        select(Chapter)
        .options(selectinload(Chapter.pages))
        .where(Chapter.series_id == series.id, Chapter.number == number, _is_live())
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    prev_number = db.scalar(
        select(func.max(Chapter.number)).where(
            Chapter.series_id == series.id, Chapter.number < number, _is_live()
        )
    )
    next_number = db.scalar(
        select(func.min(Chapter.number)).where(
            Chapter.series_id == series.id, Chapter.number > number, _is_live()
        )
    )
    return schemas.ChapterOut(
        series_slug=series.slug,
        series_title=series.title,
        format=series.format,
        reading_direction=series.reading_direction,
        number=chapter.number,
        title=chapter.title,
        pages=[schemas.PageOut.model_validate(p) for p in chapter.pages],
        body_text=chapter.body_text,
        prev_number=prev_number,
        next_number=next_number,
    )


@router.get("/{slug}/characters", response_model=list[schemas.CharacterCard])
def get_characters(
    slug: str,
    up_to_chapter: int = Query(..., ge=0, description="Furthest chapter the reader has reached"),
    db: Session = Depends(get_db),
):
    """Spoiler-safe character cards.

    Returns only characters who have appeared, and only the facts and aliases
    revealed, up to `up_to_chapter`. In step 2 this comes from the logged-in
    reader's furthest_chapter instead of a query parameter.
    """
    series = _get_visible_series(db, slug)
    characters = db.scalars(
        select(Character)
        .where(Character.series_id == series.id, Character.first_appearance_chapter <= up_to_chapter)
        .order_by(Character.first_appearance_chapter, Character.name)
    ).all()
    if not characters:
        return []

    # Filter facts in the query. Never read character.facts here: it would load
    # every fact, spoilers included.
    facts = db.scalars(
        select(CharacterFact)
        .where(
            CharacterFact.character_id.in_([c.id for c in characters]),
            CharacterFact.revealed_in_chapter <= up_to_chapter,
        )
        .order_by(CharacterFact.revealed_in_chapter, CharacterFact.sort_order)
    ).all()
    facts_by_character: dict[int, list[CharacterFact]] = defaultdict(list)
    for fact in facts:
        facts_by_character[fact.character_id].append(fact)

    return [
        schemas.CharacterCard(
            id=c.id,
            name=c.name,
            # An alias without a reveal chapter stays hidden: spoiler-safe by default
            aliases=[
                a["name"]
                for a in (c.aliases or [])
                if a.get("revealed_in_chapter") is not None
                and a["revealed_in_chapter"] <= up_to_chapter
            ],
            avatar_url=c.avatar_url,
            first_appearance_chapter=c.first_appearance_chapter,
            facts=[schemas.CharacterFactOut.model_validate(f) for f in facts_by_character[c.id]],
        )
        for c in characters
    ]
