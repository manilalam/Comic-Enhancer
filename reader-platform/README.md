# Reader Platform

Comic and novel reading platform: webtoons, manga and web novels, with spoiler-safe story context and panel-level reactions.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, PostgreSQL
- **Web:** Next.js (step 5)
- **App:** React Native with Expo (after MVP)
- **Images:** Cloudflare R2 or S3 behind a CDN (step 3)

## Step 1: Backend foundation

### What's included

- Database schema for every MVP feature (users, series, chapters, pages, characters, reading progress, library, comments, panel reactions, reports, takedowns)
- Read API: list and search series, series detail, chapter reader data, spoiler-safe character cards
- Demo data: a webtoon, a novel, and a mature manga (which should stay hidden)

### Dependencies in one folder

Every dependency lives in the `dependencies` folder at the project root:

```
dependencies/
├── python/            every Python package (.whl files)
└── postgres16.tar     the PostgreSQL Docker image
```

**Fill it once, with internet** (from the project root):

```bash
setup_dependencies.bat        # Windows
./setup_dependencies.sh       # Mac / Linux
```

**Install from it any time, no internet needed:**

```bash
install.bat                   # Windows
./install.sh                  # Mac / Linux
```

This creates `backend/.venv`, installs every package from the folder, loads the PostgreSQL image into Docker, and creates `backend/.env`.

Notes:

- Python 3.11+ and Docker Desktop are programs, not packages, so install them normally first.
- Packages are downloaded for your operating system and Python version. If you move to another OS or Python version, run the setup script again there.
- The folder is large (around 450 MB), so it's excluded from Git in `.gitignore`.
- After adding a package to `backend/requirements.txt`, run the setup script again.

### Run it

```bash
# 1. Install dependencies (see above)
install.bat                     # Mac / Linux: ./install.sh

# 2. Start PostgreSQL
docker compose up -d

# 3. Activate the environment and load demo data
cd backend
.venv\Scripts\activate          # Mac / Linux: source .venv/bin/activate
python -m scripts.seed

# 4. Start the API
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API.

### Checks

| Request | Expected |
|---|---|
| `GET /series` | 2 series. Night Market (mature) is not listed |
| `GET /series?format=novel` | Only Salt and Starlight |
| `GET /series/the-last-lantern` | Chapters 1–3. The draft chapter 4 is not listed |
| `GET /series/the-last-lantern/chapters/2` | 4 pages, `prev_number: 1`, `next_number: 3` |
| `GET /series/the-last-lantern/chapters/4` | 404 (draft) |
| `GET /series/night-market` | 404 (mature, hidden until auth) |
| `GET /series/the-last-lantern/characters?up_to_chapter=1` | Only Mira, with 1 fact and no aliases |
| `GET /series/the-last-lantern/characters?up_to_chapter=2` | Mira (2 facts) and Kade (1 fact) |
| `GET /series/the-last-lantern/characters?up_to_chapter=3` | Everything, including "The Ember Heir" alias |

The last three rows are the spoiler-safety test.

## Spoiler-safety rules

- `Character.name` is the name readers first know a character by. A real name revealed later goes in `aliases` with its `revealed_in_chapter`.
- An alias without `revealed_in_chapter` is never shown.
- Spoiler checks use the reader's **furthest** chapter, not the one they're currently on, so re-reading old chapters doesn't hide what they already know.

## MVP build order

1. ✅ Backend foundation
2. Auth (email login, then Google and phone OTP) and Alembic migrations
3. Creator upload and image processing (slicing, WebP/AVIF, R2 storage)
4. Reader state: reading progress, library, bookmarks
5. Web reader in Next.js: vertical, page and novel modes
6. Discovery: home feed, browse, search
7. Character cards in the reader, panel reactions, comments
8. Safety and admin: content ratings, reports, moderation, takedowns, admin dashboard
9. Deploy
