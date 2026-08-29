---
title: Content Recommendation Platform
emoji: 🎯
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# ContentPlatform — Personalized Recommendation System

A production-style backend that delivers a personalized content feed using a slot-based ranking engine.

🔗 **[Live Demo](https://topukumar-content-recommendation-platform.hf.space)**

> **About the live demo:** Hugging Face Spaces blocks outbound SMTP, so the demo runs with `DEMO_MODE=true` — OTPs are fixed at `123456` and email delivery is skipped. The production path (`DEMO_MODE=false`, the default) generates codes with `secrets.choice` and delivers them over SMTP. See [Demo Mode](#demo-mode).

Built with focus on:
- System design and scalability tradeoffs
- Real-world backend architecture patterns
- Security best practices
- Measurable performance optimizations

---

## Key Highlights

- **Secure auth** — JWT in httponly cookies + OTP verification with attempt limiting
- **Slot-based recommendation engine:**
  - Deterministic top slots with a per-category cap
  - Softmax sampling (temperature = 0.7) for weighted exploration
  - Time decay `exp(-t/24h)` for content freshness
  - Uniform-random and recycled slots to counteract filter bubbles
  - Seeded ordering so pagination is stable within an hour
- **Time-decayed preferences** — interactions age out with a 30-day time constant, so stale interests fade
- **Batched background scoring** — keyset paging + one grouped aggregate + one bulk upsert per batch
- **Clean architecture** — routes → services → core, fully separated concerns
- **47 unit + integration tests** — ranking engine, auth flows, admin operations, user flows
- **CI/CD pipeline** — GitHub Actions runs the full suite on every push and PR; a passing push to `main` deploys automatically to the live Space
- **Performance optimizations** — connection pooling, DB indexing, N+1 prevention, pagination
- **Load tested** — staged Locust tests from 10 to 500 concurrent users, breaking point identified and documented
- **Neural scoring experiment** — a Keras MLP trained on simulated behaviour, evaluated against baselines and **not** shipped. See [Neural Scoring Experiment](#neural-scoring-experiment)

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
| ML (experiment only) | TensorFlow/Keras, scikit-learn |
| CI/CD | GitHub Actions → Hugging Face Spaces |
| Frontend | Vanilla JS + Tailwind CSS |

---

## System Design Focus

This project emphasizes:
- **Ranking system design** — explore vs exploit, scoring tradeoffs, diversity enforcement, stable pagination
- **Backend architecture patterns** — service isolation, dependency injection, background tasks
- **Performance and scaling tradeoffs** — why batch scoring beats per-request scoring, why pagination happens after ranking
- **Security best practices** — OTP attempt limiting, JWT storage, CORS, race condition prevention
- **Honest evaluation** — a model was built, measured against baselines, and rejected on the evidence

> This is not a CRUD app. Every architectural decision has a documented reason — including the ones that are still open, listed under [Known Limitations](#known-limitations).

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
| ML (experiment only) | TensorFlow/Keras, scikit-learn, NumPy |
| CI/CD | GitHub Actions → Hugging Face Spaces |
| Frontend | HTML + Vanilla JS + Tailwind CSS |
| Server | Uvicorn |

---

## Project Structure

```
content-platform/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── env.example
├── .env                                # single source of config for local + Docker
├── .github/
│   └── workflows/
│       └── ci-cd.yml                   # test on push/PR, deploy to HF Space on pass
├── backend/
│   ├── main.py                         # app entry point, CORS, routing, scheduler
│   ├── database.py                     # SQLAlchemy engine, session, Base, connection pool
│   ├── models.py                       # all database table definitions
│   ├── scheduler.py                    # batched score recalculation (every 50 min)
│   ├── seed.py                         # 5 categories + 100 posts via the API
│   ├── conftest.py                     # pytest fixtures — TestClient, SQLite test DB
│   ├── requirements.txt
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
│   │   ├── recommendation_service.py   # ranking algorithm with complexity comments
│   │   ├── feedback_service.py         # feedback CRUD
│   │   └── admin_service.py            # user management, stats
│   ├── ml/                             # offline experiment — not on the request path
│   │   ├── simulate.py                 # synthetic browsing behaviour
│   │   ├── populate.py                 # writes synthetic users/impressions to Postgres
│   │   ├── dataset.py                  # point-in-time feature extraction + temporal split
│   │   └── train.py                    # MLP vs logistic vs heuristic, AUC comparison
│   └── tests/
│       ├── unit/
│       │   ├── test_recommendation.py  # softmax, time decay, slot logic, seed stability
│       │   └── test_auth.py            # login, signup, OTP, password validation
│       ├── integration/
│       │   ├── test_feed.py            # signup → login → feed → auth cycle, pagination shape
│       │   ├── test_admin.py           # admin block → user denied, unblock → access restored
│       │   └── test_user.py            # profile update, feedback submission, save → unsave
│       └── load/
│           ├── locustfile.py           # realistic user flow simulation
│           ├── run_tests.sh            # staged test runner, auto stop on failure
│           ├── requirements.txt        # locust dependencies
│           └── results/                # HTML + CSV reports per stage (gitignored)
└── frontend/
    ├── index.html                      # landing page with smart redirect
    ├── signup.html
    ├── verify.html                     # OTP verification + 60s resend timer
    ├── login.html
    ├── forgot-password.html
    ├── reset-password.html
    ├── feed.html                       # personalized feed + search + filter + pagination
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
- Resend OTP with 60 second cooldown timer (client-side — see [Known Limitations](#known-limitations))
- OTP attempt limiting — locked after 5 wrong attempts with countdown
- Unverified user re-signup resends OTP instead of showing error
- JWT stored in httponly cookie (protected from XSS)
- Configurable token expiry via `.env`
- Forgot password via email OTP
- Change password from profile (requires OTP verification)
- Role based access control — `user` and `admin`
- Blocked user detection on every authenticated request — denied instantly
- Email sending via FastAPI BackgroundTasks — never blocks the request path

---

### Recommendation Engine

The feed builds its entire ordering in **one pass**, in buckets of 20 — one bucket per page.

#### How Scoring Works

Every candidate post gets a combined score before ranking:

```
score = (0.7 × preference_score) + (0.3 × freshness_score) + 0.1
```

**preference_score** — how much the user likes this category, stored as a probability. Each interaction is weighted by type *and* decayed by its own age:

```
weight:  viewed → 1,  liked → 3,  saved → 5
decay:   exp(-age_in_days / 30)

raw_category = Σ (weight × decay)
preference   = raw_category / Σ all raw_category
```

The decay is what stops a user's interests from being frozen by old behaviour. Without it a view from six months ago counts exactly as much as one from yesterday, so someone whose interests shift never sees the feed follow.

```
interaction age →  weight retained
today                 100%
30 days                37%
45 days                22%
90 days                 5%
6 months              0.2%
```

> `DECAY_DAYS = 30` is a judgement call, not a fitted value. Choosing it properly means holding out a later week of real traffic and picking the time constant that best predicts it.

**freshness_score** — time decay with a 24-hour time constant:

```
freshness = exp(-hours_since_posted / 24)

1 hour ago   → 0.96
24 hours ago → 0.37
72 hours ago → 0.05
```

Exponential decay is asymptotic — posts never completely die, they just approach zero. Linear decay would hard-expire posts at an arbitrary cutoff.

**0.1 base score** — prevents any post from having zero probability.

---

#### Slot Structure

Each bucket of 20 is filled in order:

```
 5 slots  → top score, max 3 per category      deterministic exploit
 8 slots  → softmax sampled (T = 0.7)          weighted exploration
 2 slots  → uniform random, ignores score      breaks the filter bubble
 3 slots  → newest by date                     fresh content always reachable
 2 slots  → already-viewed posts               recycled variety
```

A single `seen` set spans every bucket, so no post appears twice anywhere in the ordering. If a slot type runs dry — the recycle pool empties, or the category cap blocks a pick — the bucket backfills by score rather than returning short. After the last bucket, anything the cap kept skipping is appended so no candidate is unreachable.

**Why the category cap:** without it, a user with one dominant interest gets five posts from that category at the top of *every* page, and the exploration slots below never counteract a monopoly that starts at the top.

**Why softmax sampling:** scores sit in a narrow band, so posts a few ranks apart are often near-identical in quality. Sampling lets those near-ties actually swap instead of being frozen by a strict sort. Tier 2 draws one candidate at a time and removes it — `random.choices()` samples *with* replacement, so a single `k=8` call can return duplicates and yield fewer than 8 distinct posts.

> **Honest note on effective spread:** raw scores land in roughly `[0.1, 1.1]`. Divided by `T = 0.7` the spread is ~1.4, so the highest-scored candidate is only about 4× as likely as the lowest across a large pool. The softmax slots are therefore closer to lightly-biased sampling than to sharp exploitation. Lowering the temperature or restricting the pool to the top ~50 candidates would sharpen it.

---

#### Stable Pagination

`rank_feeds` takes a `seed`. Without one, the softmax and random slots re-roll on every request — so page 2 would be sliced out of an ordering page 1 never came from, repeating some posts and hiding others.

The seed is `hash((user_id, current_hour))`:

- **Same user, same hour** → identical ordering, so page 2 genuinely continues page 1
- **Next hour** → new ordering, so the feed feels fresh on a return visit

The tradeoff: a user who crosses the hour boundary mid-scroll gets their next page from a different ordering. One boundary crossing, one possible repeat.

---

#### Candidate Pool

```
all posts
  − posts this user has already viewed        (NOT EXISTS on user_interactions)
  − filtered by search / category if supplied
  → newest FEED_LIMIT (500)
```

Viewed posts are excluded permanently. `NOT EXISTS` rather than `NOT IN`: it stops at the first matching row per post and uses the `user_id` index, instead of materialising the user's entire viewed-id list. Checking `viewed` alone is enough — liking or saving implies having viewed.

A separate query loads up to `RECYCLE_POOL_LIMIT` (100) previously-viewed posts for the recycle slots.

**New users** have no `category_preferences` rows, so `rank_feeds` returns newest-first with no slot structure. There is nothing to personalize against until the scheduler has run at least once after their first interactions.

---

#### Exhausted State

The feed response includes an `exhausted` flag, set when the user has run out of posts — either the pool is empty or they have paged past the last page.

It is suppressed when a search term or category filter is active, because "your filter matched nothing" and "you have read everything" need different messages. The frontend shows *"You're all caught up"* for the first and *"No posts found"* for the second.

---

#### Score Update Cycle

```
user interacts (view/like/save)
→ interaction recorded instantly
→ post drops out of their candidate pool immediately
→ scheduler runs every 50 minutes
→ recalculates decayed category probabilities for all active users
→ next feed load uses the updated scores
```

Category preferences therefore lag behaviour by up to 50 minutes. With a 30-day decay a handful of new interactions barely moves the shares, so the lag costs little — but it is a real gap for a brand-new user's first session.

The scheduler processes users in batches of 1000 using keyset paging (`id > last_id`, not `OFFSET`, which makes PostgreSQL walk and discard rows as the offset grows). Each batch takes **three statements**: one grouped aggregate over `(user_id, category_id)`, one scoped delete for preferences with no interaction behind them, and one `INSERT ... ON CONFLICT DO UPDATE`.

The previous implementation looped one user at a time with an exists-check before each write — roughly 7 round trips per user. Grouping by `(user_id, category_id)` rather than `category_id` alone is what lets a single query cover the whole batch.

Each batch commits independently and failures are logged with a traceback, so one bad batch does not roll back the users already scored. `last_id` advances before the work, so a failing batch cannot wedge the loop on the same ids.

---

### Feed
- Personalized order based on the slot algorithm
- Paginated API — `GET /feed?page=1&limit=20` returns `{ items, total, page, pages, exhausted }`
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

## Neural Scoring Experiment

An offline experiment testing whether a learned model beats the hand-tuned scoring formula. **It does not run in production** — the code lives in `backend/ml/` and is not imported by any route or service.

### What was built

| file | role |
|---|---|
| `simulate.py` | generates synthetic browsing behaviour from an explicit rule |
| `populate.py` | writes synthetic users, impressions and interactions to Postgres |
| `dataset.py` | builds labelled rows with point-in-time correct features, splits by time |
| `train.py` | trains a Keras MLP, compares it against logistic regression and the heuristic |

**Impression logging.** `user_interactions` only records actions, so a post that was shown and ignored looks identical to one that was never shown. An `impressions` table records every (user, post) pair displayed, which is what makes an honest negative label possible: *shown and not viewed* rather than *absent from the interactions table*.

**Point-in-time correctness.** Every aggregate is computed with `created_at < shown_at`. Using present-day totals for a past row leaks future information into the features — the model then scores well offline while having nothing real to say at serving time, when the future genuinely does not exist yet.

**Temporal split.** Train on the earlier 75%, test on the most recent 25%. A random split would train on later behaviour and test on earlier behaviour, inflating the score in a way that does not reproduce in production.

### Result

AUC on the held-out window (~29k impressions, ~21% positive):

| model | AUC |
|---|---|
| heuristic formula | 0.7830 |
| logistic regression | 0.7843 |
| Keras MLP (11 → 16 → 8 → 1) | 0.7856 |

All three are within 0.003 — a tie. **The model was not shipped**, because there is no measured gain to justify a TensorFlow dependency, a model file, feature extraction on the request path, and a retraining job.

### What this result does and does not show

It does **not** establish that the production formula is good for real users. The evaluation ran entirely on simulated data, and every parameter of that simulation — the base view probability, the per-category decay half-lives, the like and save probabilities — was chosen by hand rather than measured. The models converge because the generating process is simple and fully exposed by the feature set; a richer, messier process is exactly where extra model capacity would be expected to pay off.

What it does show is a correctly built evaluation pipeline: impression-based labelling, point-in-time features, a temporal split, class-weighted training, and a comparison against both the incumbent heuristic and a linear baseline. Pointed at real traffic, it would give a real answer. The middle rung matters — without a linear baseline, a good MLP number would not distinguish "the network earned its complexity" from "any fitted model would have done as well."

### Running it

```bash
cd backend
python ml/populate.py     # requires seeded categories and posts
python ml/train.py        # prints the three AUCs, saves scorer.keras + scaler.pkl
```

`populate.py` inserts synthetic users and impressions. Do not run it against a database with real users.

---

## Demo Mode

`DEMO_MODE` exists because the public demo host blocks outbound SMTP.

| | `DEMO_MODE=false` (default) | `DEMO_MODE=true` |
|---|---|---|
| OTP generation | `secrets.choice` — 6 random digits | fixed `123456` |
| Email delivery | Gmail SMTP via `BackgroundTasks` | skipped, code logged to stdout |
| Intended for | local development, production | the hosted demo, CI |

The frontend never hardcodes the demo code. `verify.html`, `reset-password.html` and `profile.html` each read `GET /config` and only autofill when `demo_mode` is true, so switching the flag changes the UI without a code change.

The test suite sets `DEMO_MODE=true` in `conftest.py` before importing the app, so the suite runs with no network access at all.

---

## Load Testing

Load tested using [Locust](https://locust.io/) with realistic concurrent user simulation.

> **These results predate the ranking rewrite.** They were measured against the earlier per-request tier implementation with a 30-connection pool. The bottleneck identified — connection pool exhaustion — is structural and still applies, but the exact numbers have not been re-measured since.

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
- **Pool at time of test:** `pool_size=10`, `max_overflow=20` (30 max connections)

> Tests ran locally on Windows 11. The same app on a dedicated Linux server would handle more concurrent users.
>
> The pool has since been reduced to `pool_size=5`, `max_overflow=5` (10 max connections) to fit the connection limits of the managed Postgres instance used for the hosted demo. A smaller pool reaches the same bottleneck sooner.

### Results

| Concurrent Users | Success Rate | p95 Latency | RPS | Status |
|---|---|---|---|---|
| 10 | 100% | ~200ms | 5 | ✅ |
| 100 | 99% | ~800ms | 50 | ✅ |
| 500 | 74% | 5100ms | 50 | ❌ Breaking point |

Stable to ~100 concurrent users; degraded significantly at 500.

### Why It Breaks at 500 Users

Two root causes identified from failure statistics:

**1. DB connection pool exhausted:**
```
pool_size=10 + max_overflow=20 = 30 max connections (configuration under test)

/feed alone hits DB 3 times per request:
  → verify JWT user
  → fetch the candidate pool
  → fetch user preferences

500 users × 3 DB hits = 1500 simultaneous DB requests
against a pool of 30 → 1470 requests waiting → timeouts
```

**2. Single Uvicorn process:**
```
Ranking is CPU-bound (scoring and sorting the candidate pool)
Single process = single core
500 concurrent users queued behind one thread
/feed p95 latency spiked to 35,000ms under 500 users
```

**Failure breakdown at 500 users:**
```
RemoteDisconnected  → Uvicorn closed connection, queue full
500 Server Error    → DB pool exhausted, query failed
p95 /feed           → 35,000ms
p95 /auth/login     → 5,300ms
Overall success     → 74%
```

> The rewrite added a fourth query per feed request (the recycle pool), so the per-request DB cost is now 4 rather than 3. That makes the pool bottleneck arrive marginally sooner, not later.

### How to Run Load Tests

```bash
cd backend/tests/load
pip install -r requirements.txt

export LOAD_TEST_DB_URL="postgresql://postgres:yourpassword@localhost:5432/contentplatform"

# app running in another terminal
uvicorn main:app --host 0.0.0.0 --port 8000

bash run_tests.sh
```

Stages run automatically: 10 → 100 → 500 → 1000 → 2000 → 3000 → 5000 users. Stops when success rate drops below 95% or p95 latency exceeds 2000ms. Each stage saves an HTML report and CSV to `results/`.

---

## Security

- **OTP attempt limiting** — locked after 5 wrong attempts, countdown shown to user, force resend
- **JWT in httponly cookie** — protected from XSS. `samesite` is set from the request scheme: `lax` over HTTP (local development), `none` + `secure` over HTTPS, which the hosted demo requires because it runs inside an iframe. See [Known Limitations](#known-limitations) for the CSRF consequence.
- **Blocked user enforcement** — every authenticated route depends on `get_current_active_user`, which re-reads the user from the database on each request. `admin_only` is built on the same check, so a block or role change takes effect immediately rather than at token expiry.
- **DB-level unique constraint** on `(user_id, feed_id, action)` — prevents race condition on duplicate interactions
- **CORS restricted** — `ALLOWED_ORIGINS` configured via environment variable, no wildcard in production
- **No default credentials** — `DATABASE_URL` and `SECRET_KEY` have no fallback values. A missing `.env` stops the app at startup instead of booting against an empty database with a publicly known signing key.
- **Secrets stay out of the image** — `.dockerignore` excludes `.env` from the build context; Compose injects configuration as environment variables at runtime
- **Explicit transaction control** — `autocommit=False`, changes only persist on `db.commit()`

---

## Performance

- **Connection pooling** — `pool_size=5`, `max_overflow=5`, `pool_timeout=30`, `pool_recycle=300`. Tuned for a managed Postgres instance with a low connection ceiling; raise both values on self-hosted Postgres.
- **Batched scheduler** — keyset paging in batches of 1000, three statements per batch regardless of batch size. Replaced a per-user loop that made roughly 7 round trips each.
- **N+1 prevention** — feed queries use SQLAlchemy `joinedload` for a single SQL JOIN; the scheduler uses one grouped aggregate per batch instead of one query per user.
- **Commit ordering on the detail route** — the response is built before the view interaction is recorded. SQLAlchemy expires the session on commit, so committing first would discard the eagerly-loaded `category` and `author` and trigger three extra queries per post view.
- **DB index on `feeds(created_at)`** — faster candidate fetching and date-ordered slots
- **Hashmap for category lookups** — `pref_map = {category_id: score}` gives O(1) lookup per post
- **Pagination** — max 20 posts per response, ranking happens on the full pool then sliced
- **Background email** — OTP sending via `BackgroundTasks`, response never waits for Gmail

---

## Known Limitations

Documented rather than hidden. These are the open items a reviewer would find.

**A user who skips everything cannot reach older posts.** The candidate pool is the newest `FEED_LIMIT` (500) unseen posts. Skipping leaves no record — only viewing does — so a user who pages through all 500 without opening any gets the same 500 back on the next request. Posts beyond 500 stay unreachable until they view something or new posts push the window. Fixing this properly needs impression logging on the request path, or cursor-based windowing. Not currently a live problem: the corpus is smaller than the pool.

**`total` and `pages` describe the candidate pool, not the corpus.** `FEED_LIMIT` caps the pool at 500, so `total` saturates there no matter how many posts exist.

**The whole ordering is rebuilt on every request.** `rank_feeds` scores and orders the full pool to serve 20 posts. At the current scale this is microseconds; at 50,000 candidates per user it would need a cached ranked ID list per user. The Redis pre-computed feed under [How This Scales](#3-recommendation-engine--per-request-ranking-at-scale) is the structural fix.

**Preferences lag behaviour by up to 50 minutes.** A new user's first session is served newest-first with no personalization at all, because the scheduler has not yet written their preferences. Triggering a one-off recalculation after a user's first N interactions would close the onboarding gap.

**Freshness decay is one constant for every category.** `TIME_DECAY_HOURS = 24` applies equally to every topic, but a two-day-old news post and a two-day-old explainer are not equally stale. Per-category half-lives would be a real improvement — but they have to be *measured* from real traffic (view rate bucketed by post age, per category), not invented. Shipping guessed constants would be worse than one honest shared value.

**Hour-boundary pagination.** The ordering seed rotates hourly. A user who crosses the boundary mid-scroll gets their next page from a different ordering, so one post may repeat or be skipped at that transition.

**OTP resend has no server-side throttle.** The 60-second cooldown lives in `verify.html`. `create_otp` deletes the previous row and inserts a new one with `attempts=0`, so a scripted client can reset the attempt counter indefinitely. The 5-attempt limit is a UX guardrail, not a brute-force defence; per-email rate limiting on `/auth/resend-otp` is the fix.

**CSRF is unmitigated when `samesite=none`.** Over HTTPS the cookie is sent cross-site, which the iframe demo needs, so state-changing POSTs are reachable from another origin. A double-submit CSRF token is the correct fix; `samesite=lax` (the local default) avoids the issue entirely.

**No migrations.** Schema changes are applied by hand via the SQL in the manual setup path. Alembic is the right tool once the schema starts moving.

**`record_interaction` relies on `IntegrityError` for repeat views.** Every view after the first raises and rolls back. It is correct but uses exceptions as control flow on a hot path; `INSERT ... ON CONFLICT DO NOTHING` is cleaner.

**The `impressions` table is written only by the ML simulator.** It is not populated by the running application, so it cannot currently support retraining on real behaviour. Doing that would mean writing a row per post served, with the storage and write-path cost that implies.

---

## Tests

47 tests across unit and integration:

```bash
cd backend
pytest tests/ -v
```

**Unit tests — `tests/unit/`**
- `test_recommendation.py` — softmax sums to 1.0, time decay never zero, category cap, no duplicates across buckets, every candidate reachable, same seed gives same order, different seed reshuffles, recycled slots fill, empty recycle pool backfills
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

The two tests worth calling out are `test_same_seed_gives_same_order` and `test_rank_feeds_no_duplicate_posts`. Both cover properties that would break *silently* under a refactor — a lost seed or a reintroduced duplicate raises no error, it just quietly degrades the feed.

Integration tests run against a file-backed SQLite database created and dropped per test — no PostgreSQL required. `conftest.py` sets `TESTING`, `DEMO_MODE`, `DATABASE_URL` and `SECRET_KEY` in `os.environ` **before** importing the app, because Pydantic reads settings at import time. The suite therefore needs no `.env` and no secrets, attempts no SMTP connection, and runs fully offline. `TESTING=true` also suppresses APScheduler startup, so no background threads spawn during the run.

Run pytest from `backend/`. The app uses flat imports (`from database import Base`), so `backend/` must be on `sys.path`; running from the repository root fails at collection rather than as a test failure.

The `ml/` directory is not covered by the suite. It is an offline experiment with no production path, and training is too slow for a test run.

---

## CI/CD

Every push and pull request to `main` runs the full test suite. A push to `main` that passes deploys automatically to the live Hugging Face Space. Tests are the gate — a failing suite blocks the release, so the deployed demo always reflects a green build.

Defined in `.github/workflows/ci-cd.yml`.

### Pipeline

```
push / PR to main
       │
       ▼
  ┌──────────┐
  │   test   │   Python 3.11 · pytest tests/ -v
  └──────────┘
       │
   pass│  │fail ──▶ pipeline stops, nothing deploys
       ▼
  ┌──────────┐
  │  deploy  │   push events only — PRs are tested, never deployed
  └──────────┘
       │
       ▼
  Hugging Face Space (force push to the Space git remote)
```

### Test job

- `ubuntu-latest`, Python 3.11, dependencies from `backend/requirements.txt`
- Runs with `working-directory: backend` — required for the flat import layout
- **No secrets required.** `conftest.py` sets every environment variable the app needs before importing it, so the suite is fully self-configuring
- Runs against a file-backed SQLite database created and dropped per test. No PostgreSQL service container needed
- `TESTING=true` suppresses APScheduler startup, so no background threads spawn during the run

### Deploy job

- `needs: test` — runs only if the test job succeeded
- `if: github.event_name == 'push'` — pull requests are validated but never deployed
- Force-pushes the repository to the Hugging Face Space git remote, which triggers a Space rebuild

### Required GitHub secrets

| Secret | Purpose |
|---|---|
| `HF_TOKEN` | Write access to the Space |
| `HF_USERNAME` | Space owner |
| `HF_SPACE_NAME` | Space name |

### Required Space variables

The Space needs its own runtime configuration. `DATABASE_URL` and `SECRET_KEY` have no defaults, so a missing value exits the container at startup with a Pydantic `ValidationError` rather than falling back to something wrong.

| Variable | Value |
|---|---|
| `DATABASE_URL` | Managed Postgres connection string |
| `SECRET_KEY` | Long random string |
| `DEMO_MODE` | `true` — Hugging Face Spaces blocks outbound SMTP |
| `REQUIRE_DB_SSL` | `true` for Neon or Supabase |
| `ALLOWED_ORIGINS` | The Space URL |

Set these under Settings → Variables and secrets on the Space. A green pipeline with missing Space variables produces a successful deploy followed by a crash loop.

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
  unique: (user_id, category_id)        ← required by the scheduler's ON CONFLICT upsert

impressions                              ← written by the ML simulator only
  id, user_id (FK), feed_id (FK), shown_at
  indexes: (user_id), (feed_id, shown_at)

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
                                   returns { items, total, page, pages, exhausted }
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

### Meta
```
GET  /health                       liveness check
GET  /config                       public runtime flags — { demo_mode, demo_otp }
```

---

## Setup

### Option 1 — Docker (recommended, one command)

1. Clone the repository
   ```bash
   git clone https://github.com/topukumar538/content-recommendation-platform.git
   cd content-recommendation-platform
   ```

2. Create your `.env` file at the repository root:
   ```bash
   cp env.example .env
   ```
   > `.env` lives at the root, not inside `backend/`. `config.py` resolves it as an absolute path from `__file__`, and Docker Compose reads the same file for both the `db` and `app` services — one file, one source of truth.

3. Fill in your real values in `.env`:
   ```env
   # Manual runs use localhost; Compose overrides the host to `db` inside the container
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/contentplatform
   SECRET_KEY=any-long-random-string
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_DAYS=7
   LOGIN_EXPIRE_TIME=7
   OTP_EXPIRE_MIN=10
   GMAIL_USER=yourgmail@gmail.com
   GMAIL_PASSWORD=your-gmail-app-password
   ALLOWED_ORIGINS=http://localhost:8000
   POSTGRES_PASSWORD=yourpassword
   DEMO_MODE=true
   REQUIRE_DB_SSL=false
   ```
   > `POSTGRES_PASSWORD` must be set — Compose uses it to initialise Postgres and to build the container's `DATABASE_URL`. It must match the password in `DATABASE_URL`.
   > `DATABASE_URL` and `SECRET_KEY` are required and have no defaults. A missing or misplaced `.env` fails at startup instead of silently falling back to a throwaway SQLite database.
   > `REQUIRE_DB_SSL` must be `false` for the compose Postgres, which runs without TLS. Set it to `true` for managed Postgres (Neon, Supabase).
   > Leave `DEMO_MODE=true` if you would rather not configure email. For real OTP delivery set it to `false` and supply a Gmail App Password: Google Account → Security → 2-Step Verification → App Passwords.

4. Run:
   ```bash
   docker compose up --build
   ```

5. Access the app at `http://localhost:8000`
   > The container serves on port 7860 (Hugging Face convention); compose maps host `8000` → container `7860`. The `Uvicorn running on 0.0.0.0:7860` line in the logs is the container's own view — use 8000 from your browser.

6. Create admin account — open a new terminal:
   ```bash
   docker exec -it contentplatform_db psql -U postgres -d contentplatform
   ```
   ```sql
   UPDATE users SET role = 'admin' WHERE email = 'youremail@gmail.com';
   \q
   ```
   Logout and login again — the role is now re-read from the database on every request.

7. Seed test data (optional) — 5 categories and 100 posts:
   ```bash
   cd backend
   python seed.py
   ```
   Posts are all created within seconds of each other, so freshness scores will be nearly identical. Spread them out to see the decay work:
   ```sql
   UPDATE feeds SET created_at = NOW() - (random() * INTERVAL '28 days');
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
   > Changing `.env` does not affect a running container. Apply changes with `docker compose up -d --force-recreate app`.

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

5. Create `.env` at the repository root:
   ```env
   # Manual setup: host is localhost
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/contentplatform
   SECRET_KEY=any-long-random-string
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_DAYS=7
   LOGIN_EXPIRE_TIME=7
   OTP_EXPIRE_MIN=10
   GMAIL_USER=yourgmail@gmail.com
   GMAIL_PASSWORD=your-gmail-app-password
   ALLOWED_ORIGINS=http://localhost:8000
   DEMO_MODE=true
   REQUIRE_DB_SSL=false
   ```
   Confirm it resolves before going further:
   ```bash
   cd backend
   python -c "from core.config import settings; print(settings.DATABASE_URL, settings.DEMO_MODE)"
   ```

6. Apply database indexes and constraints
   ```bash
   sudo -u postgres psql -d contentplatform
   ```
   ```sql
   CREATE INDEX ix_feeds_created_at_desc ON feeds (created_at DESC);
   ALTER TABLE otp_codes ADD COLUMN IF NOT EXISTS attempts INTEGER DEFAULT 0;
   ALTER TABLE user_interactions ADD CONSTRAINT uq_user_feed_action UNIQUE (user_id, feed_id, action);
   ALTER TABLE category_preferences ADD CONSTRAINT uq_user_category UNIQUE (user_id, category_id);
   ```
   > The last one is required by the scheduler's `ON CONFLICT DO UPDATE`. It is also declared in `models.py`, so a database created fresh by `create_all` already has it; the ALTER is for an existing database.

7. Run the server from `backend/`
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```
   > `--reload` watches `.py` files only. After editing `.env`, restart the process manually.

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
Routes handle HTTP only — request parsing and response formatting. Services contain all business logic with no HTTP dependency. The ranking algorithm is fully isolated in `recommendation_service.py`, making it independently testable and easy to swap without touching any route.

**Seeded ordering for stable pagination**
`rank_feeds` samples in its softmax and random slots. Without a fixed seed, two calls produce two different orderings — so page 2 would be sliced out of a list page 1 never came from, repeating some posts and hiding others. Seeding on `(user_id, hour)` makes the ordering stable for anyone browsing within the hour, while still giving a fresh arrangement on a return visit. This replaced an earlier implementation where the instability was a documented bug.

**One ranking pass, not one per page**
The entire ordering is built in a single pass with a shared `seen` set spanning every bucket. Building each page independently would need a way to know what earlier pages contained, which is exactly the state the seed avoids carrying.

**Decaying interactions rather than counting them**
Weighting a six-month-old view the same as yesterday's freezes a user's interests permanently. An exponential decay with a 30-day time constant means preferences follow current behaviour without any hard cutoff — nothing disappears on a particular day, it just counts progressively less.

**httponly cookies for JWT**
Storing the JWT in an httponly cookie prevents JavaScript from reading it, protecting against XSS. `samesite=lax` over plain HTTP prevents CSRF; the hosted demo runs in an iframe over HTTPS and therefore needs `samesite=none`, which trades that protection away until a CSRF token is added.

**Two auth dependencies, deliberately**
`get_current_user` decodes the JWT and nothing else. `get_current_active_user` additionally re-reads the user row on every request. Tokens live for 7 days, so without the second check a user blocked at minute 1 would keep full access for the remaining 7 days. Every route that acts on behalf of a user — including `admin_only` — uses the DB-backed version; the cost is one indexed primary-key lookup.

**Fail loudly on missing configuration**
`DATABASE_URL` and `SECRET_KEY` have no defaults. An earlier version defaulted to `sqlite:///./app.db` and a hardcoded signing key, which meant a missing `.env` produced a running app pointed at an empty database — the symptom surfaced as broken login rather than broken config. Paths follow the same rule: `.env` and the frontend directory are both resolved as absolute paths from `__file__`.

**Errors are surfaced, not swallowed**
OTP delivery failures are logged with a full traceback rather than discarded inside a background task, where a 200 response would otherwise hide a dead SMTP connection. FastAPI returns 422 validation errors as a list of objects, so a `RequestValidationError` handler flattens them to a string — without it the frontend renders `[object Object]`.

**Softmax temperature at 0.7**
A temperature of 0.3 would make sampling almost deterministic. A temperature of 2.0 would make all posts equally likely. At 0.7 the algorithm favours high-scoring posts while still giving lower-scoring ones a meaningful chance. See the honest note above on how much spread this actually produces at the current score range.

**Batched scheduled scoring over instant updates**
Recalculating on every interaction would mean a write per user per action. One batched job covers all users in three statements per 1000. The cost is a lag of up to 50 minutes before preferences reflect new behaviour — acceptable because the 30-day decay means a handful of interactions barely moves the shares anyway.

**Keyset paging, not OFFSET, in the scheduler**
`OFFSET 999000` makes PostgreSQL walk and discard 999,000 rows before returning anything. `WHERE id > :last_id` uses the primary key index and stays fast at any depth.

**Exponential time decay for freshness**
Linear decay would make posts score zero after a fixed time. `exp(-hours/24)` is asymptotic — posts never completely die but approach zero. This mirrors how real content platforms treat recency.

**Timezone-aware datetime comparison**
All timestamp columns are `DateTime(timezone=True)`. Comparisons convert to UTC with `astimezone`/`now(timezone.utc)` rather than stripping the offset with `.replace(tzinfo=None)`, which silently shifts every result by the server's UTC offset. Naive values (SQLite, in tests) are assumed UTC.

**Category cap in the top slots**
Without the cap, a user with one dominant interest would get five posts from that category at the top of every page, and the exploration slots below would never counteract a monopoly that starts at the top. Posts blocked by the cap are not discarded — they remain eligible for later slots and for later buckets.

**Like/Save as toggle with DB cleanup**
When a user unlikes a post the interaction row is deleted, not flagged. The scheduler deletes preference rows with no interaction behind them in the same pass, so scores only reflect genuine current preferences.

**is_active vs is_blocked separation**
`is_active` tracks whether a user has verified their email. `is_blocked` tracks whether an admin has restricted access. Keeping them separate allows independent control.

**autocommit=False**
Explicit transaction control means changes only persist when `db.commit()` is called, preventing accidental partial writes and allowing clean rollback on failure.

**N+1 prevention in two places**
Feed queries use `joinedload` to fetch category and author in a single JOIN — without it, accessing `feed.category.name` for 100 posts fires 200 extra queries. The scheduler computes category weights with one grouped aggregate per batch rather than per user.

**Explicit ORDER BY before LIMIT**
The candidate pool is ordered by `created_at DESC` before the limit is applied. Without an explicit `ORDER BY`, PostgreSQL returns an arbitrary subset once the table exceeds the limit.

**NOT EXISTS over NOT IN for viewed posts**
`NOT IN (SELECT ...)` materialises the user's entire viewed-id list to test membership. `NOT EXISTS` stops at the first matching row per post and uses the `user_id` index.

**DB-level unique constraint on interactions**
App-level deduplication alone has a race condition — two simultaneous requests can both pass the check before either commits. The database constraint on `(user_id, feed_id, action)` guarantees correctness regardless of concurrency.

**Pagination after ranking**
Pagination happens after ranking, not at the query level. The algorithm needs the full pool to make meaningful decisions. Slicing before ranking would return reasonable posts for that page but poor overall personalization.

**The neural scorer was measured, then rejected**
Building a model and shipping it because you built it is the common failure mode. The MLP was compared against both the incumbent heuristic and a linear baseline on a temporal split, tied with both, and was therefore not deployed. A negative result honestly reported is more useful than a positive one that does not survive scrutiny.

---

## Ranking Algorithm Parameters

All parameters are named constants in `recommendation_service.py`:

| Parameter | Value | Description |
|---|---|---|
| `FEED_LIMIT` | 500 | Max unseen posts fetched per request |
| `RECYCLE_POOL_LIMIT` | 100 | Max previously-viewed posts loaded for recycle slots |
| `BUCKET_SIZE` | 20 | Posts per bucket — matches the default page size |
| `SLOT_TOP` | 5 | Deterministic top-scored slots per bucket |
| `SLOT_WEIGHTED` | 8 | Softmax-sampled slots per bucket |
| `SLOT_RANDOM` | 2 | Uniform random slots per bucket |
| `SLOT_NEWEST` | 3 | Date-ordered slots per bucket |
| `SLOT_RECYCLED` | 2 | Already-viewed slots per bucket |
| `TOP_MAX_PER_CAT` | 3 | Max posts per category within the top slots |
| `SOFTMAX_TEMPERATURE` | 0.7 | Exploration sharpness (lower = more deterministic) |
| `PREF_WEIGHT` | 0.7 | Weight of preference score in the combined score |
| `FRESH_WEIGHT` | 0.3 | Weight of freshness score in the combined score |
| `BASE_SCORE` | 0.1 | Minimum score floor |
| `TIME_DECAY_HOURS` | 24 | Post freshness time constant. Half-life `24·ln2 ≈ 16.6h` |

And in `scheduler.py`:

| Parameter | Value | Description |
|---|---|---|
| `BATCH_SIZE` | 1000 | Users scored per round trip |
| `DECAY_DAYS` | 30 | Interaction age time constant. A judgement call, not fitted |
| `ACTION_WEIGHTS` | 1 / 3 / 5 | viewed / liked / saved |

---

## Environment Variables

All variables are read from a single `.env` at the repository root. Docker Compose reads the same file, so local and containerised runs share one source of truth.

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string — **required**, no default | `postgresql://postgres:pass@localhost:5432/contentplatform` |
| `SECRET_KEY` | JWT signing secret — **required**, no default | any long random string |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_DAYS` | JWT payload expiry in days | `7` |
| `LOGIN_EXPIRE_TIME` | Cookie max age in days | `7` |
| `OTP_EXPIRE_MIN` | OTP validity window in minutes | `10` |
| `GMAIL_USER` | Gmail address for sending OTPs | `yourapp@gmail.com` |
| `GMAIL_PASSWORD` | Gmail App Password | 16-character app password |
| `ALLOWED_ORIGINS` | Allowed CORS origin | `http://localhost:8000` |
| `POSTGRES_PASSWORD` | PostgreSQL password for Docker | same as password in DATABASE_URL |
| `DEMO_MODE` | Fixed OTP, no email delivery | `false` locally, `true` on the hosted demo |
| `REQUIRE_DB_SSL` | Force `sslmode=require` on the Postgres connection | `false` for Docker, `true` for Neon/Supabase |
| `TESTING` | Suppresses scheduler startup — set by `conftest.py`, not by hand | `false` |

`DATABASE_URL` and `SECRET_KEY` are deliberately left without defaults. An app that boots against the wrong database is harder to diagnose than one that refuses to boot.

---

## How This Scales to 1M Users

The measured architecture handles ~100 concurrent users comfortably (99% success, ~800ms p95). Here is what breaks at scale and how to fix each one. These are design directions, not implemented work.

---

### 1. DB Connection Pool — First bottleneck

**Problem:** The pool exhausts under concurrent load. The load test confirmed this — `/feed` p95 spiked to 35,000ms at 500 users with 30 connections available. The current 10-connection pool reaches the same wall sooner, and the rewrite added a fourth query per request.

**Solution:**
- **PgBouncer** — connection pooler in front of PostgreSQL, multiplexes many app connections into a small efficient pool
- **Read replicas** — route SELECT queries to replicas, writes to primary
- **Partitioning** — partition `user_interactions` by `user_id`. At 1M users × 50 interactions = 50M rows

---

### 2. Single Uvicorn Process — Second bottleneck

**Problem:** CPU-bound ranking blocks the event loop. One core handling all requests.

**Solution:**
- **Multiple workers** — `uvicorn main:app --workers 4` uses all cores, no code changes
- **Nginx load balancer** — distribute traffic across instances
- **Horizontal scaling** — stateless JWT design means any number of servers can run behind a load balancer

> Caveat: the in-process APScheduler is per-process. Four workers means four schedulers recalculating the same users, and four separate connection pools. Moving the scheduler out — item 4 — is a prerequisite for adding workers.

---

### 3. Recommendation Engine — Per-request ranking at scale

**Problem:** Every `/feed` request scores and orders the full candidate pool to serve 20 posts.

**Solution:**
- **Pre-compute feeds** — run ranking in the background, store each user's ranked ID list in Redis
- **Redis sorted sets** — `user:{id}:feed` with post IDs scored by rank. Feed request becomes `ZRANGE` in O(log N)
- Trade-off: the feed is slightly stale versus perfectly fresh — acceptable for most platforms
- This also removes the hour-boundary pagination edge case, since the ordering becomes a stored artifact rather than a seeded recomputation

---

### 4. Scheduler — Single in-process APScheduler

**Problem:** At 1M users, one batch job competes with request handling.

**Solution:**
- **Celery + Redis** — each batch becomes an independent distributed task
- **Celery Beat** triggers the run, workers process batches in parallel

The batching and keyset paging already in place are the prerequisite for this — the work is already partitioned into independent chunks.

---

### 5. Gmail SMTP — Email sending limit

**Problem:** Gmail SMTP caps around 500 emails/day.

**Solution:**
- Replace with **AWS SES or SendGrid**
- Already architected for it — one function swap in `otp_service.py`

---

### 6. Static Files — Served by FastAPI

**Problem:** FastAPI serving HTML/CSS/JS wastes server resources at scale.

**Solution:**
- **CDN (Cloudflare or CloudFront)** — static files from edge nodes, FastAPI handles API only

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
Celery Beat (scheduler)
```

### What stays the same
- Ranking algorithm logic — the scoring and slot structure need no changes
- JWT auth — stateless, works across any number of servers
- Database schema — needs partitioning and replicas, not redesign
- The test suite — no changes needed