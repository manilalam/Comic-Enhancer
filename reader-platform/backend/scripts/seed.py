"""Load demo data. Run from the backend folder: python -m scripts.seed"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app import models  # noqa: F401
from app.db import Base, SessionLocal, engine
from app.models import (
    Chapter, Character, CharacterFact, ContentRating, Page, ReadingDirection,
    Series, SeriesFormat, Tag, User, UserRole,
)

NOW = datetime.now(timezone.utc)


def placeholder(chapter: int, page: int) -> str:
    return f"https://placehold.co/800x1280/png?text=Ch{chapter}+Page{page}"


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == "creator@example.com")):
            print("Demo data already loaded.")
            return

        creator = User(email="creator@example.com", display_name="Demo Creator", role=UserRole.creator)
        tags = {
            name: Tag(name=name, kind=kind)
            for name, kind in [("Fantasy", "genre"), ("Action", "genre"),
                               ("Romance", "genre"), ("Slow burn", "tag")]
        }

        # Webtoon: 3 live chapters, 1 draft (should never appear in the API)
        lantern = Series(
            creator=creator, title="The Last Lantern", slug="the-last-lantern",
            description="A lantern-keeper in a border town discovers what the light holds back.",
            format=SeriesFormat.webtoon, ownership_confirmed_at=NOW,
            tags=[tags["Fantasy"], tags["Action"]],
        )
        for n in range(1, 5):
            ch = Chapter(
                number=n, title=f"Episode {n}",
                published_at=NOW - timedelta(days=10 - n) if n <= 3 else None,
            )
            ch.pages = [Page(page_number=p, image_url=placeholder(n, p), width=800, height=1280)
                        for p in range(1, 5)]
            lantern.chapters.append(ch)

        mira = Character(
            name="Mira", first_appearance_chapter=1,
            aliases=[{"name": "The Ember Heir", "revealed_in_chapter": 3}],
            facts=[
                CharacterFact(text="Keeps the last lantern burning in the border town of Vel.", revealed_in_chapter=1),
                CharacterFact(text="Can see the spirits the lantern holds back.", revealed_in_chapter=2),
                CharacterFact(text="Heir to the fallen Ember Court.", revealed_in_chapter=3),
            ],
        )
        kade = Character(
            name="Kade", first_appearance_chapter=2,
            facts=[
                CharacterFact(text="A courier who smuggles letters across the border.", revealed_in_chapter=2),
                CharacterFact(text="Was secretly sent to find Mira.", revealed_in_chapter=3),
            ],
        )
        lantern.characters.extend([mira, kade])

        # Novel: text chapters
        novel = Series(
            creator=creator, title="Salt and Starlight", slug="salt-and-starlight",
            description="Two rival navigators are forced onto the same ship.",
            format=SeriesFormat.novel, ownership_confirmed_at=NOW,
            tags=[tags["Romance"], tags["Slow burn"]],
        )
        novel.chapters = [
            Chapter(number=1, title="The Wrong Ship", published_at=NOW - timedelta(days=3),
                    body_text="The harbour smelled of tar and rain...\n\n(Demo chapter text.)"),
            Chapter(number=2, title="North by Starlight", published_at=NOW - timedelta(days=1),
                    body_text="By the third night, neither of them would admit to being lost...\n\n(Demo chapter text.)"),
        ]

        # Manga, right-to-left, mature: should be hidden from every endpoint for now
        mature = Series(
            creator=creator, title="Night Market", slug="night-market",
            format=SeriesFormat.manga, reading_direction=ReadingDirection.rtl,
            content_rating=ContentRating.mature, ownership_confirmed_at=NOW,
        )
        mature.chapters = [Chapter(number=1, title="Opening", published_at=NOW - timedelta(days=2))]

        db.add_all([creator, lantern, novel, mature])
        db.commit()
        print("Demo data loaded: 3 series, 1 creator.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
