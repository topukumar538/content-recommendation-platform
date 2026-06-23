---
title: My First Space
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
sdk_version: "4.29.0"
python_version: "3.10"
app_file: app.py
pinned: false
---

# ContentPlatform — Personalized Recommendation System 
 
A production-style backend system that delivers a personalized content feed using a multi-tier recommendation engine.

Built with focus on:
- System design and scalability tradeoffs
- Real-world backend architecture patterns
- Security best practices
- Measurable performance optimizations

---

## Key Highlights

- **Secure auth** — JWT in httponly cookies + OTP verification with brute force protection
- **Advanced recommendation engine:**
  - Softmax sampling (temperature=0.7) for controlled randomness
  - Time decay `exp(-t/24h)` for content freshness
  - Explore vs exploit strategy — prevents filter bubbles
  - Category diversity constraints in Tier 1
- **Background job processing** — batch score updates every 10 min, email off request path
- **Clean architecture** — routes → services → core, fully separated concerns
- **42 unit + integration tests** — recommendation engine, auth flows, admin operations, user flows
- **Performance optimizations** — connection pooling, DB indexing, N+1 prevention, pagination
- **Load tested** — staged Locust tests from 10 to 500 concurrent users, breaking point identified and documented

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Scheduler | APScheduler |
| Testing | Pytest + Locust |
| Frontend | Vanilla JS + Tailwind CSS |

---

## System Design Focus

This project emphasizes:
- **Recommendation system design** — explore vs exploit, scoring tradeoffs, diversity enforcement
- **Backend architecture patterns** — service isolation, dependency injection, background tasks
- **Performance and scaling tradeoffs** — why batch scoring beats per-request scoring, why pagination happens after ranking
- **Security best practices** — OTP rate limiting, JWT storage, CORS, race condition prevention
- **Load testing** — scientifically measured breaking point with root cause analysis

> This is not a CRUD app. Every architectural decision has a documented reason.

---

## Tech Stack (Detailed)

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Authentication | JWT (httponly cookies) |
| Email | Gmail SMTP (OTP delivery via BackgroundTasks) |
| Password Hashing | bcrypt + passlib |
| Scheduler | APScheduler |
| Testing | Pytest (unit + integration) + Locust (load testing) |
| Frontend | HTML + Vanilla JS + Tailwind CSS |
| Server | Uvicorn |

---

## Project Structure

```
content-platform/
├── Dockerfile
├── docker-compose.yml
├── env.example
├── backend/
│   ├── main.py                         # app entry point, CORS, routing, scheduler
│   ├── database.py                     # SQLAlchemy engine, session, Base, connection pool
│   ├── models.py                       # all database table definitions
│   ├── scheduler.py                    # background score recalculation (every 10 min)
│   ├── conftest.py                     # pytest fixtures — TestClient, SQLite test DB
│   ├── requirements.txt
│   ├── .env
│   ├── core/
│   │   ├── config.py                   # centralized settings from .env
│   │   ├── security.py                 # JWT, password hashing
│   │   └── dependencies.py             # route guards, auth helpers
│   ├── schemas/
│   │   ├── auth.py                     # signup, login, OTP, password schemas
│   │   ├── feed.py                     # feed create/update/response schemas
│   │   ├── category.py                 # category schemas
│   │   ├── feedback.py                 # feedback schemas
│   │   └── user.py                     # profile update schema
│   ├── routes/
│   │   ├── auth.py                     # /auth/* endpoints
│   │   ├── feed.py                     # /feed/* and /categories/* endpoints
│   │   ├── admin.py                    # /admin/* endpoints
│   │   └── user.py                     # /user/* endpoints
│   ├── services/
│   │   ├── auth_service.py             # signup, login, OTP, password logic
│   │   ├── otp_service.py              # OTP generation, email sending, verification
│   │   ├── feed_service.py             # feed, categories, interactions, pagination
│   │   ├── recommendation_service.py   # full recommendation algorithm with complexity comments
│   │   ├── feedback_service.py         # feedback CRUD
│   │   └── admin_service.py            # user management, stats
│   └── tests/
│       ├── unit/
│       │   ├── test_recommendation.py  # softmax, time decay, tier logic, edge cases
│       │   └── test_auth.py            # login, signup, OTP, password validation
│       ├── integration/
│       │   ├── test_feed.py            # signup → login → feed → auth cycle, pagination shape, duplicate signup
│       │   ├── test_admin.py           # admin block → user denied, unblock → access restored, non-admin rejected
│       │   └── test_user.py            # profile update, feedback submission, full save → unsave flow
│       └── load/
│           ├── locustfile.py           # realistic user flow simulation
│           ├── run_tests.sh            # staged test runner 10 → 5000 users, auto stop on failure
│           ├── requirements.txt        # locust dependencies
│           └── results/               # HTML + CSV reports per stage (gitignored)
└── frontend/
    ├── index.html                      # landing page with smart redirect
    ├── signup.html
    ├── verify.html                     # OTP verification + 60s resend timer
    ├── login.html
    ├── forgot-password.html
    ├── reset-password.html
    ├── feed.html                       # personalized feed + search + category filter + pagination
    ├── feed-detail.html                # post detail + like + save + related posts
    ├── saved.html                      # saved posts with unsave option
    ├── profile.html                    # update username + change password via OTP
    ├── feedback.html                   # star rating (1-5) + message
    ├── admin.html                      # dashboard stats + categories + posts
    ├── admin-users.html                # view, block/unblock, delete users
    └── admin-feedback.html             # view, resolve, delete feedback
```

---

## Features

### Authentication
- Signup with email OTP verification
- Resend OTP with 60 second cooldown timer
- OTP brute force protection — locked after 5 wrong attempts with countdown
- Unverified user re-signup resends OTP instead of showing error
- JWT stored in httponly cookie (protected from XSS)
- Configurable token expiry via `.env`
- Forgot password via email OTP
- Change password from profile (requires OTP verification)
- Role based access control — `user` and `admin`
- Blocked user detection on every authenticated request — denied instantly
- Email sending via FastAPI BackgroundTasks — never blocks the request path

### Recommendation Engine

The feed uses a **3-tier Softmax Explore vs Exploit algorithm** with time decay scoring.

#### How Scoring Works

Every post gets a combined score before ranking:

```
score = (0.7 × preference_score) + (0.3 × freshness_score) + 0.1
```

> Note: this raw score is not normalized — it is later passed through Softmax in Tier 2 to convert scores into probabilities. Tier 1 uses raw scores for deterministic ranking.

**preference_score** — how much the user likes this category, stored as a probability:
```
viewed → weight 1
liked  → weight 3
saved  → weight 5

example: user has 10 Technology interactions, 5 Science interactions
Technology score = 10 / 15 = 0.67
Science score    = 5  / 15 = 0.33
```

**freshness_score** — time decay using exponential decay over 24 hours:
```
freshness = exp(-hours_since_posted / 24)

post from 1 hour ago   → exp(-1/24)  = 0.96  (very fresh)
post from 24 hours ago → exp(-1)     = 0.37  (moderately fresh)
post from 72 hours ago → exp(-3)     = 0.05  (mostly stale)
```

Exponential decay is asymptotic — posts never completely die, they just approach zero. This mirrors how real content platforms treat recency. Linear decay would hard-expire posts at an arbitrary cutoff.

**0.1 base score** — prevents any post from having zero probability, ensuring no content is completely dead.

---

#### What is Softmax and Why It Is Used

Softmax converts a list of raw scores into probabilities that sum to exactly 1.0. This allows weighted random selection — higher scored posts are more likely to be selected, but lower scored posts still have a chance.

**The formula:**
```
softmax(score) = exp(score / temperature) / sum(exp(all scores / temperature))
```

**Temperature controls exploration sharpness:**
```
temperature = 0.3 → very sharp → high scores dominate almost completely
temperature = 0.7 → balanced  → high scores likely but low scores still have chance
temperature = 2.0 → very flat → all posts get nearly equal probability

this project uses temperature = 0.7 for balanced exploration
```

**Example with 3 posts:**
```
raw scores: [0.8, 0.5, 0.2]
after softmax (temperature=0.7):
  post A → 0.65 probability (likely but not guaranteed)
  post B → 0.25 probability (moderate chance)
  post C → 0.10 probability (small but real chance)

without softmax (greedy):
  post A → always selected (no variety)
```

This is the same mechanism used in ChatGPT's temperature slider — higher temperature means more creative/random responses, lower temperature means more predictable responses.

---

#### 3-Tier Feed Algorithm

```
TIER 1 (slots 1–15)   → deterministic exploit          O(F log F)
                         top 15 posts by combined score
                         max 3 posts per category enforced
                         ensures diversity, prevents one topic dominating

TIER 2 (slots 16–20)  → softmax weighted exploration   O(F)
                         5 posts selected by weighted random sampling
                         high score = more likely, not guaranteed
                         gives variety — posts user might not have seen

TIER 3 (slots 21+)    → newest unseen posts             O(F log F)
                         all remaining posts ordered by date
                         ensures fresh content is always discoverable

EPSILON               → 10% chance of one truly random post
                         injected anywhere in the feed
                         breaks any remaining filter bubble
```

**Why this structure:**
- Pure exploitation (always show highest scored) creates a filter bubble — users only see what they already like
- Pure exploration (always random) makes personalization useless
- This 3-tier structure balances both — users see relevant content first, discover new content second, and always have access to fresh posts

**Overall complexity: O(F log F) time, O(F) space** where F = number of posts fetched (max 500)

---

#### Score Update Cycle

Scores are recalculated every 10 minutes by a background scheduler:

```
user interacts (view/like/save)
→ interaction recorded instantly in UserInteractions table
→ scheduler runs every 10 minutes
→ recalculates category probability scores for all active users
→ stores updated scores in CategoryPreferences table
→ next feed load uses updated scores
```

Scheduled recalculation scales better than instant updates — one batch job for all users every 10 minutes is more efficient than one database write per interaction per user at scale.

---

### Feed
- Personalized order based on recommendation algorithm
- Paginated API — `GET /feed?page=1&limit=20` returns `{ items, total, page, pages }`
- Search by title or content (case insensitive)
- Filter by category
- Related posts on detail page (same category, excluding current)
- Like and save with toggle — click to like, click again to unlike. State persists on reload
- Frontend pagination controls with Previous / Next navigation

### User Features
- Saved posts collection with unsave option
- Profile page — update username
- Change password with OTP verification
- Star rating feedback submission (1–5) with message

### Admin Panel
- Dashboard stats — total users, posts, interactions, feedback
- Category management — create and delete
- Post management — create and delete
- User management — view all users, block/unblock, delete
- Feedback management — view, resolve/unresolve, delete

---

## Load Testing

Load tested using [Locust](https://locust.io/) with realistic concurrent user simulation.

### Test Flow Per Virtual User
```
signup → verify OTP (fetched directly from DB) → login
→ browse feed → view post → like → save → search → logout → repeat
```

Each virtual user creates a real account and loops through weighted actions:
```
31%   feed browsing      (most common real user action)
19%   post viewing
12.5% liking posts
12.5% saving posts
6%    searching
6%    pagination
6%    logout and back
6%    viewing saved posts
```

### Test Environment
- **CPU:** Intel Core Ultra 7
- **RAM:** 8GB
- **Storage:** 512GB SSD
- **OS:** Windows 11
- **Server:** Single Uvicorn process, no caching, no Redis

> Note: Tests run locally on Windows 11. Same app on a dedicated Linux server would handle significantly more concurrent users — Windows handles concurrent connections less efficiently than Linux.

### Results

| Concurrent Users | Success Rate | p95 Latency | RPS | Status |
|---|---|---|---|---|
| 10 | 100% | ~200ms | 5 | ✅ Perfect |
| 100 | 99% | ~800ms | 50 | ✅ Excellent |
| 500 | 74% | 5100ms | 50 | ❌ Breaking point |

**Stable up to ~100 users. Degraded significantly at 500 (74% success rate, 5100ms p95) on current setup**
= approximately **5,000–10,000 daily active users** on a single unoptimized server

### Why It Breaks at 500 Users

Two root causes identified from failure statistics:

**1. DB connection pool exhausted:**
```
pool_size=10 + max_overflow=20 = 30 max connections

/feed alone hits DB 3 times per request:
  → verify JWT user
  → fetch 500 posts with joinedload
  → fetch user preferences

500 users × 3 DB hits = 1500 simultaneous DB requests
against a pool of 30 → 1470 requests waiting → timeouts
```

**2. Single Uvicorn process:**
```
Recommendation algorithm is CPU-bound (sorting 500 posts)
Single process = single core
500 concurrent users queued behind one thread
/feed p95 latency spiked to 35,000ms under 500 users
```

**Failure breakdown at 500 users:**
```
RemoteDisconnected  → Uvicorn closed connection, queue full
500 Server Error    → DB pool exhausted, query failed
p95 /feed           → 35,000ms (35 seconds)
p95 /auth/login     → 5,300ms
Overall success     → 74%
```

### How to Run Load Tests

```bash
# install locust
cd backend/tests/load
pip install -r requirements.txt

# update DB_URL in locustfile.py with your PostgreSQL password

# make sure app is running in another terminal
uvicorn main:app --host 0.0.0.0 --port 8000

# run all staged tests automatically
bash run_tests.sh
```

Tests run stages automatically: 10 → 100 → 500 → 1000 → 2000 → 3000 → 5000 users.
Stops when success rate drops below 95% or p95 latency exceeds 2000ms.
Each stage saves an HTML report and CSV to `results/`.

---

## Security

- **OTP rate limiting** — locked after 5 wrong attempts, countdown shown to user, force resend
- **JWT in httponly cookie** — protected from XSS, `samesite=lax` prevents CSRF
- **Blocked user enforcement** — every authenticated route uses `get_current_active_user`, blocked users denied instantly on next request
- **DB-level unique constraint** on `(user_id, feed_id, action)` — prevents race condition on duplicate interactions
- **CORS restricted** — `ALLOWED_ORIGINS` configured via environment variable, no wildcard in production
- **Explicit transaction control** — `autocommit=False`, changes only persist on `db.commit()`

---

## Performance

- **Connection pooling** — `pool_size=10`, `max_overflow=20`, `pool_timeout=30`, `pool_recycle=1800`
- **N+1 prevention** — all feed queries use SQLAlchemy `joinedload` for single SQL JOIN
- **DB index on `feeds(created_at DESC)`** — faster feed fetching and Tier 3 date ordering
- **Hashmap for category lookups** — `pref_map = {category_id: score}` gives O(1) lookup per post
- **Pagination** — max 20 posts per response, ranking happens on full pool then sliced
- **Background email** — OTP sending via `BackgroundTasks`, response never waits for Gmail

---

## Tests

42 tests across unit and integration:

```bash
pytest tests/ -v
```

**Unit tests — `tests/unit/`**
- `test_recommendation.py` — softmax sums to 1.0, time decay never zero, tier diversity, no duplicates, preferred category ranks higher
- `test_auth.py` — login failure cases, signup validation, password mismatch, blocked user

**Integration tests — `tests/integration/`**
- `test_feed.py` — signup → login → feed → auth cycle, pagination shape, duplicate signup
- `test_admin.py` — admin block → user denied, unblock → access restored, non-admin rejected from admin routes
- `test_user.py` — profile update, feedback submission, full save → unsave flow

**Load tests — `tests/load/`**
- Staged concurrent user simulation using Locust
- Realistic user flows with weighted task distribution
- Auto-stop on failure conditions
- HTML + CSV reports per stage

All integration tests use SQLite in-memory DB — no real PostgreSQL needed to run tests.

---

## Database Schema

```
users
  id, username, email, password, role, is_active, is_blocked, created_at

otp_codes
  id, email, code, purpose, is_used, attempts, created_at

categories
  id, name

feeds
  id, title, content, category_id (FK), author_id (FK), created_at
  indexes: ix_feeds_created_at_desc

user_interactions
  id, user_id (FK), feed_id (FK), action, created_at
  unique: (user_id, feed_id, action)

category_preferences
  id, user_id (FK), category_id (FK), score, updated_at

feedbacks
  id, user_id (FK), message, rating, is_resolved, created_at
```

---

## API Endpoints

### Auth — `/auth`
```
POST /signup                       register new account
POST /verify-otp                   verify email OTP (max 5 attempts)
POST /resend-otp                   resend OTP (60s cooldown on frontend)
POST /login                        login, sets httponly cookie
POST /logout                       clears cookie
POST /forgot-password              send reset OTP to email
POST /reset-password               verify OTP and set new password
POST /request-change-password-otp  send OTP to logged-in user's email
POST /change-password              verify OTP and change password
GET  /me                           get current user info
```

### Feed — `/feed`
```
GET    /feed                       personalized feed (?search= &category_id= &page= &limit=)
GET    /feed/{id}                  post detail, records view interaction
GET    /feed/{id}/interactions     get like/save state for a post
POST   /feed/{id}/like             toggle like — adds if not liked, removes if liked
POST   /feed/{id}/save             toggle save — adds if not saved, removes if saved
POST   /feed                       create post (admin only)
PUT    /feed/{id}                  update post (admin only)
DELETE /feed/{id}                  delete post (admin only)
```

### Categories — `/categories`
```
GET    /categories                 list all categories
POST   /categories                 create category (admin only)
PUT    /categories/{id}            update category (admin only)
DELETE /categories/{id}            delete category (admin only)
```

### User — `/user`
```
GET    /user/saved                 get saved posts
DELETE /user/saved/{id}            unsave a post
POST   /user/feedback              submit feedback
PATCH  /user/profile               update username
```

### Admin — `/admin`
```
GET    /admin/stats                platform statistics
GET    /admin/users                all users
PATCH  /admin/users/{id}/block     block or unblock user
DELETE /admin/users/{id}           delete user and all their data
GET    /admin/feedback             all feedback
PATCH  /admin/feedback/{id}/resolve toggle resolved status
DELETE /admin/feedback/{id}        delete feedback
```

---

## Setup

### Option 1 — Docker (recommended, one command)

1. Clone the repository
   ```bash
   git clone https://github.com/topukumar538/content-recommendation-platform.git
   cd content-recommendation-platform
   ```

2. Create your `.env` file inside `backend/`:
   ```bash
   cp env.example backend/.env
   ```

3. Fill in your real values in `backend/.env`:
   ```env
   DATABASE_URL=postgresql://postgres:yourpassword@db:5432/contentplatform
   SECRET_KEY=any-long-random-string
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_DAYS=7
   LOGIN_EXPIRE_TIME=7
   OTP_EXPIRE_MIN=10
   GMAIL_USER=yourgmail@gmail.com
   GMAIL_PASSWORD=your-gmail-app-password
   ALLOWED_ORIGINS=http://localhost:8000
   POSTGRES_PASSWORD=yourpassword
   ```
   > `POSTGRES_PASSWORD` and the password in `DATABASE_URL` must match.
   > Gmail App Password: Google Account → Security → 2-Step Verification → App Passwords

4. Run:
   ```bash
   docker compose up --build
   ```

5. Access the app at `http://localhost:8000`

6. Create admin account — open a new terminal:
   ```bash
   docker exec -it contentplatform_db psql -U postgres -d contentplatform
   ```
   ```sql
   UPDATE users SET role = 'admin' WHERE email = 'youremail@gmail.com';
   \q
   ```
   Logout and login again to get a new token with admin role.

7. Seed test data (optional) — 5 categories and 100 posts:
   ```bash
   cd backend
   python seed.py
   ```

8. Run tests:
   ```bash
   cd backend
   pytest tests/ -v
   ```

9. Stop the app:
   ```bash
   docker compose down        # stop containers
   docker compose down -v     # stop and delete database data
   ```

---

### Option 2 — Manual setup (without Docker)

1. Clone the repository
   ```bash
   git clone https://github.com/topukumar538/content-recommendation-platform.git
   cd content-recommendation-platform
   ```

2. Create virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Create PostgreSQL database
   ```bash
   sudo -u postgres psql
   CREATE DATABASE contentplatform;
   \q
   ```

5. Create `backend/.env`:
   ```env
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/contentplatform
   SECRET_KEY=any-long-random-string
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_DAYS=7
   LOGIN_EXPIRE_TIME=7
   OTP_EXPIRE_MIN=10
   GMAIL_USER=yourgmail@gmail.com
   GMAIL_PASSWORD=your-gmail-app-password
   ALLOWED_ORIGINS=http://localhost:8000
   ```

6. Apply database indexes
   ```bash
   sudo -u postgres psql -d contentplatform
   ```
   ```sql
   CREATE INDEX ix_feeds_created_at_desc ON feeds (created_at DESC);
   ALTER TABLE otp_codes ADD COLUMN IF NOT EXISTS attempts INTEGER DEFAULT 0;
   ALTER TABLE user_interactions ADD CONSTRAINT uq_user_feed_action UNIQUE (user_id, feed_id, action);
   ```

7. Run the server
   ```bash
   uvicorn main:app --reload --port 8000
   ```

8. Access the app at `http://localhost:8000`

9. Create admin account
   ```bash
   sudo -u postgres psql -d contentplatform
   ```
   ```sql
   UPDATE users SET role = 'admin' WHERE email = 'youremail@gmail.com';
   \q
   ```

10. Seed test data (optional)
    ```bash
    python seed.py
    ```

11. Run tests
    ```bash
    pytest tests/ -v
    ```

---

## Key Design Decisions

**Routes vs Services separation**
Routes handle HTTP only — request parsing and response formatting. Services contain all business logic with no HTTP dependency. The recommendation algorithm is fully isolated in `recommendation_service.py`, making it independently testable and easy to swap or upgrade without touching any route or other service.

**httponly cookies for JWT**
Storing the JWT in an httponly cookie prevents JavaScript from reading it, protecting against XSS attacks. The cookie is set with `samesite=lax` to prevent CSRF.

**Softmax temperature at 0.7**
A temperature of 0.3 would make softmax almost deterministic — high scored posts would dominate completely. A temperature of 2.0 would make all posts equally likely. At 0.7 the algorithm favors high scored posts while still giving lower scored posts a meaningful chance. This is the same temperature concept used in large language models.

**Scheduled score updates over instant updates**
Recalculating scores every 10 minutes in a batch job scales better than recalculating on every single interaction. At small scale the difference is negligible. At large scale — thousands of concurrent users — instant per-interaction recalculation would create excessive database writes. The batch approach means one scheduled job updates all users efficiently.

**Time decay with exponential function**
Linear decay (subtract a fixed amount per hour) would make old posts score zero after a fixed time. Exponential decay using `exp(-hours/24)` is asymptotic — posts never completely die but their freshness approaches zero over time. This mirrors how real content platforms treat recency.

**Category diversity enforcement in Tier 1**
Without the max-3-per-category limit, Tier 1 could be dominated by 15 posts from a single category the user heavily interacted with. The limit ensures users always see variety in their top results even when they have a strong preference for one topic.

**Like/Save as toggle with DB cleanup**
When a user unlikes a post the interaction row is deleted from the database — not just flagged. This keeps the interactions table clean and ensures the recommendation engine only scores genuine current preferences, not historical ones the user has reversed.

**is_active vs is_blocked separation**
`is_active` tracks whether a user has verified their email. `is_blocked` tracks whether an admin has restricted access. Keeping them separate allows independent control — an unverified user is not the same as a blocked one.

**autocommit=False**
Explicit transaction control means changes only persist when `db.commit()` is called. This prevents accidental partial writes and allows clean rollback on failure.

**N+1 prevention with joinedload**
All feed queries use SQLAlchemy `joinedload` to fetch related category and author data in a single SQL JOIN. Without this, accessing `feed.category.name` for 100 posts would fire 200 extra database queries.

**OTP rate limiting**
After 5 wrong attempts the OTP is locked and the user must request a new one. With a 6-digit OTP (999,999 combinations) and a 60-second resend cooldown, brute force becomes practically impossible — an attacker would need 200,000 resend requests to exhaust all combinations.

**Background email sending**
OTP emails are sent via FastAPI `BackgroundTasks` — the response is returned immediately and email is sent after. If Gmail is slow or down, the user experience is unaffected. Previously, a slow Gmail response would block the entire signup request.

**DB-level unique constraint on interactions**
App-level deduplication alone has a race condition — two simultaneous requests can both pass the check before either commits. The database-level unique constraint on `(user_id, feed_id, action)` guarantees correctness regardless of concurrency.

**Connection pool configuration**
Explicit `pool_size=10`, `max_overflow=20`, `pool_recycle=1800` prevents connection exhaustion under concurrent load and ensures stale connections are recycled every 30 minutes.

**Pagination after ranking**
Pagination happens after the recommendation algorithm ranks all posts — not at the DB query level. The algorithm needs the full pool to make meaningful ranking decisions. Slicing before ranking would return good posts for that page but poor overall personalization.

---

## Recommendation Algorithm Parameters

All algorithm parameters are defined as named constants in `recommendation_service.py`:

| Parameter | Value | Description |
|---|---|---|
| `FEED_LIMIT` | 500 | Max posts fetched from database per request |
| `TIER1_SIZE` | 15 | Number of deterministic top scored posts |
| `TIER1_MAX_PER_CAT` | 3 | Max posts per category in Tier 1 |
| `TIER2_SIZE` | 5 | Number of softmax sampled wildcard posts |
| `SOFTMAX_TEMPERATURE` | 0.7 | Exploration sharpness (lower = more deterministic) |
| `EPSILON` | 0.1 | Probability of injecting a truly random post |
| `PREF_WEIGHT` | 0.7 | Weight given to preference score in combined score |
| `FRESH_WEIGHT` | 0.3 | Weight given to freshness score in combined score |
| `BASE_SCORE` | 0.1 | Minimum score floor to prevent zero probability |
| `TIME_DECAY_HOURS` | 24 | Half-life of freshness decay in hours |

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:pass@localhost:5432/contentplatform` |
| `SECRET_KEY` | JWT signing secret | any long random string |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_DAYS` | JWT payload expiry in days | `7` |
| `LOGIN_EXPIRE_TIME` | Cookie max age in days | `7` |
| `OTP_EXPIRE_MIN` | OTP validity window in minutes | `10` |
| `GMAIL_USER` | Gmail address for sending OTPs | `yourapp@gmail.com` |
| `GMAIL_PASSWORD` | Gmail App Password | 16-character app password |
| `ALLOWED_ORIGINS` | Allowed CORS origin | `http://localhost:8000` |
| `POSTGRES_PASSWORD` | PostgreSQL password for Docker | same as password in DATABASE_URL |

---

## How This Scales to 1M Users

Current architecture handles ~100 concurrent users comfortably (99% success rate, ~800ms p95).
Here is what breaks at scale and how to fix each one.

---

### 1. DB Connection Pool — First bottleneck

**Problem:** Pool of 30 connections exhausts at ~100 concurrent users. Load test confirmed this — `/feed` p95 spiked to 35,000ms at 500 users due to connection queue buildup.

**Solution:**
- **PgBouncer** — connection pooler in front of PostgreSQL, multiplexes thousands of app connections into a small efficient pool
- **Read replicas** — route all SELECT queries (feed, search) to replicas, writes go to primary
- **Partitioning** — partition `user_interactions` by `user_id`. At 1M users × 50 interactions = 50M rows

---

### 2. Single Uvicorn Process — Second bottleneck

**Problem:** CPU-bound ranking algorithm blocks the event loop. One core handling all requests.

**Solution:**
- **Multiple workers** — `uvicorn main:app --workers 4` uses all CPU cores, 4x throughput immediately, zero code changes
- **Nginx load balancer** — distribute traffic across multiple server instances
- **Horizontal scaling** — stateless JWT design means any number of servers can run behind a load balancer

---

### 3. Recommendation Engine — Per-request ranking at scale

**Problem:** Every `/feed` request fetches 500 posts and runs the full ranking algorithm. At 1M concurrent users = 500M post objects in memory simultaneously.

**Solution:**
- **Pre-compute feeds** — run ranking in background scheduler, store each user's ranked feed in Redis
- **Redis sorted sets** — `user:{id}:feed` with post IDs scored by rank. Feed request = `ZRANGE` in O(log N) instead of O(F log F)
- Trade-off: feed is slightly stale (up to 10 min) vs perfectly fresh — acceptable for most platforms

---

### 4. Scheduler — Single in-process APScheduler

**Problem:** At 1M users, recalculating scores every 10 min in one batch takes too long and competes with request handling.

**Solution:**
- **Celery + Redis** — each user's score recalculation becomes an independent distributed task
- **Celery Beat** triggers the batch, workers process users in parallel across a worker pool

---

### 5. Gmail SMTP — Email sending limit

**Problem:** Gmail SMTP limit ~500 emails/day. Breaks immediately at scale.

**Solution:**
- Replace with **AWS SES or SendGrid** — SES costs ~$0.10 per 1000 emails
- Already architected correctly — one function swap in `otp_service.py`

---

### 6. Static Files — Served by FastAPI

**Problem:** FastAPI serving HTML/CSS/JS wastes server resources at scale.

**Solution:**
- **CDN (Cloudflare or CloudFront)** — static files served from edge nodes globally, FastAPI handles API only

---

### Scaled Architecture at 1M Users

```
Users
  ↓
Cloudflare CDN (static files + DDoS protection)
  ↓
Nginx Load Balancer
  ↓           ↓           ↓
FastAPI     FastAPI     FastAPI     (4 workers each)
  ↓
Redis (pre-computed feeds, OTP cache, sessions)
  ↓
PgBouncer
  ↓
PostgreSQL Primary → Read Replicas
  ↑
Celery Workers (score recalculation)
  ↑
Celery Beat (scheduler every 10 min)
```

### What stays the same
- Recommendation algorithm logic — scales without changes
- JWT auth — stateless, works across any number of servers
- Database schema — just needs partitioning and replicas
- All existing tests — zero changes needed