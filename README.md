# ContentPlatform

A full-stack personalized content platform built with FastAPI and PostgreSQL. Features a recommendation engine using an Explore vs Exploit algorithm, JWT authentication with email OTP verification, and a complete admin panel.

Built as a portfolio project to demonstrate backend engineering skills.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Authentication | JWT (httponly cookies) |
| Email | Gmail SMTP (OTP delivery) |
| Password Hashing | bcrypt + passlib |
| Scheduler | APScheduler |
| Frontend | HTML + Vanilla JS + Tailwind CSS |
| Server | Uvicorn |

---

## Project Structure

```
content-platform/
├── backend/
│   ├── main.py                    # app entry point, CORS, routing, scheduler
│   ├── database.py                # SQLAlchemy engine, session, Base
│   ├── models.py                  # all database table definitions
│   ├── scheduler.py               # background score recalculation (every 10 min)
│   ├── requirements.txt
│   ├── .env
│   ├── core/
│   │   ├── config.py              # centralized settings from .env
│   │   ├── security.py            # JWT, password hashing
│   │   └── dependencies.py        # route guards, auth helpers
│   ├── schemas/
│   │   ├── auth.py                # signup, login, OTP, password schemas
│   │   ├── feed.py                # feed create/update/response schemas
│   │   ├── category.py            # category schemas
│   │   ├── feedback.py            # feedback schemas
│   │   └── user.py                # profile update schema
│   ├── routes/
│   │   ├── auth.py                # /auth/* endpoints
│   │   ├── feed.py                # /feed/* and /categories/* endpoints
│   │   ├── admin.py               # /admin/* endpoints
│   │   └── user.py                # /user/* endpoints
│   └── services/
│       ├── auth_service.py        # signup, login, OTP, password logic
│       ├── otp_service.py         # OTP generation, email sending, verification
│       ├── feed_service.py        # feed, categories, interactions, recommendation
│       ├── feedback_service.py    # feedback CRUD
│       └── admin_service.py       # user management, stats
└── frontend/
    ├── index.html                 # landing page with smart redirect
    ├── signup.html
    ├── verify.html                # OTP verification + 60s resend timer
    ├── login.html
    ├── forgot-password.html
    ├── reset-password.html
    ├── feed.html                  # personalized feed + search + category filter
    ├── feed-detail.html           # post detail + like + save + related posts
    ├── saved.html                 # saved posts with unsave option
    ├── profile.html               # update username + change password via OTP
    ├── feedback.html              # star rating (1-5) + message
    ├── admin.html                 # dashboard stats + categories + posts
    ├── admin-users.html           # view, block/unblock, delete users
    └── admin-feedback.html        # view, resolve, delete feedback
```

---

## Features

### Authentication
- Signup with email OTP verification
- Resend OTP with 60 second cooldown timer
- Unverified user re-signup resends OTP instead of showing error
- JWT stored in httponly cookie (protected from XSS)
- Configurable token expiry via `.env`
- Forgot password via email OTP
- Change password from profile (requires OTP verification)
- Role based access control — `user` and `admin`
- Blocked user detection on every authenticated request

### Recommendation Engine

Feed is ordered using an **Explore vs Exploit** algorithm:

```
First 20 posts  → highest preference score        (exploit known interests)
Next 20 posts   → newest posts not in first 20    (explore new content)
Remaining       → score × 0.5 + recency × 0.5    (balanced mixture)
```

Interaction weights used to calculate preference scores:
```
viewed → weight 1
liked  → weight 3
saved  → weight 5
```

Scores are stored as probabilities per category per user and recalculated every 10 minutes by a background scheduler. This means the feed reorders periodically based on accumulated interactions rather than on every single action, keeping the experience stable while still personalizing over time.

### Feed
- Personalized order based on user preference scores
- Search by title or content (case insensitive)
- Filter by category
- Related posts on detail page (same category, excluding current)
- Like and save with instant visual feedback

### User Features
- Saved posts collection with unsave option
- Profile page — update username
- Change password with OTP verification
- Star rating feedback submission (1–5) with message

### Admin Panel
- Dashboard stats — total users, posts, interactions, feedback
- Most liked and most saved post tracking
- Category management — create and delete
- Post management — create and delete
- User management — view all users, block/unblock, delete
- Feedback management — view, resolve/unresolve, delete

---

## Database Schema

```
users
  id, username, email, password, role, is_active, is_blocked, created_at

otp_codes
  id, email, code, purpose, is_used, created_at

categories
  id, name

feeds
  id, title, content, category_id (FK), author_id (FK), created_at

user_interactions
  id, user_id (FK), feed_id (FK), action, created_at

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
POST /verify-otp                   verify email OTP
POST /resend-otp                   resend OTP
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
GET    /feed                       personalized feed (?search= &category_id=)
GET    /feed/{id}                  post detail, records view interaction
POST   /feed/{id}/like             like post
POST   /feed/{id}/save             save post
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

### 1. Clone the repository
```bash
git clone https://github.com/topukumar538/content-platform.git
cd content-platform
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Create PostgreSQL database
```bash
sudo -u postgres psql
CREATE DATABASE contentplatform;
\q
```

### 5. Create `.env` file inside `backend/`
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/contentplatform
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=7
LOGIN_EXPIRE_TIME=7
OTP_EXPIRE_MIN=10
GMAIL_USER=yourgmail@gmail.com
GMAIL_PASSWORD=your-gmail-app-password
```

> **Gmail App Password:** Google Account → Security → 2-Step Verification → App Passwords → create one for "ContentPlatform"

### 6. Run the server
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 7. Access the app
```
App        →  http://localhost:8000/
API docs   →  http://localhost:8000/docs
```

### 8. Create admin account

First sign up normally, then run:
```bash
sudo -u postgres psql -d contentplatform
```
```sql
UPDATE users SET role = 'admin' WHERE email = 'youremail@gmail.com';
\q
```
Logout and login again to get a new token with admin role.

### 9. Seed test data (optional)

Creates 5 categories and 100 posts for testing:
```bash
cd backend
python seed.py
```
Update the email and password at the top of `seed.py` before running.

---

## Key Design Decisions

**Routes vs Services separation**
Routes handle HTTP only — request parsing and response formatting. Services contain all business logic with no HTTP dependency. This makes services independently testable and reusable.

**httponly cookies for JWT**
Storing the JWT in an httponly cookie prevents JavaScript from reading it, protecting against XSS attacks. The cookie is set with `samesite=lax` to prevent CSRF.

**Scheduled score updates**
Preference scores are recalculated every 10 minutes by a background scheduler rather than on every single interaction. This keeps the feed stable — scores accumulate meaningfully over time instead of reordering after every click. Interactions are still recorded instantly; only the score recalculation is batched.

**Explore vs Exploit algorithm**
Without exploration, users get stuck seeing only content similar to what they have already interacted with — a filter bubble. Without exploitation, personalization has no effect. The split balances both: the top 20 slots reward known preferences, the next 20 introduce discovery, and the rest blend both signals.

**is_active vs is_blocked separation**
`is_active` tracks whether a user has verified their email. `is_blocked` tracks whether an admin has restricted access. Keeping them separate allows independent control — an unverified user is not the same as a blocked one.

**autocommit=False**
Explicit transaction control means changes only persist when `db.commit()` is called. This prevents accidental partial writes and allows clean rollback on failure.

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
