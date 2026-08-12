import random
import string
from locust import HttpUser, task, between, events
from sqlalchemy import create_engine, text

# ── DB connection (same as your app) ──────────────────────────
import os
DB_URL = os.environ.get("LOAD_TEST_DB_URL", "postgresql://postgres:password@localhost:5432/contentplatform")
engine = create_engine(DB_URL)


def get_otp_from_db(email: str) -> str:
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT code FROM otp_codes
                WHERE email = :email
                AND purpose = 'signup'
                AND is_used = false
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"email": email}
        )
        row = result.fetchone()
        return row[0] if row else None


def random_email() -> str:
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"loadtest_{suffix}@test.com"


class ContentPlatformUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.email = random_email()
        self.password = "123456"
        self.feed_ids = []
        self.is_registered = False
        self._signup()

    def _signup(self):
        res = self.client.post("/auth/signup", json={
            "username": f"user_{self.email[:10]}",
            "email": self.email,
            "password": self.password
        }, name="/auth/signup")

        if res.status_code != 200:
            return

        code = get_otp_from_db(self.email)
        if not code:
            return

        res = self.client.post("/auth/verify-otp", json={
            "email": self.email,
            "code": code,
            "purpose": "signup"
        }, name="/auth/verify-otp")

        if res.status_code != 200:
            return

        self._login()

    def _login(self):
        res = self.client.post("/auth/login", json={
            "email": self.email,
            "password": self.password
        }, name="/auth/login")

        if res.status_code == 200:
            self.is_registered = True

    def _logout(self):
        self.client.post("/auth/logout", name="/auth/logout")
        self.is_registered = False

    @task(5)
    def view_feed(self):
        if not self.is_registered:
            self._login()
            return
        res = self.client.get("/feed?page=1&limit=20", name="/feed")
        if res.status_code == 200:
            data = res.json()
            self.feed_ids = [item["id"] for item in data.get("items", [])]

    @task(3)
    def view_post(self):
        if not self.is_registered or not self.feed_ids:
            return
        post_id = random.choice(self.feed_ids)
        self.client.get(f"/feed/{post_id}", name="/feed/{id}")

    @task(2)
    def like_post(self):
        if not self.is_registered or not self.feed_ids:
            return
        post_id = random.choice(self.feed_ids)
        self.client.post(f"/feed/{post_id}/like", name="/feed/{id}/like")

    @task(2)
    def save_post(self):
        if not self.is_registered or not self.feed_ids:
            return
        post_id = random.choice(self.feed_ids)
        self.client.post(f"/feed/{post_id}/save", name="/feed/{id}/save")

    @task(1)
    def view_feed_page2(self):
        if not self.is_registered:
            return
        self.client.get("/feed?page=2&limit=20", name="/feed?page=2")

    @task(1)
    def search_feed(self):
        if not self.is_registered:
            return
        keywords = ["python", "health", "science", "business", "sports"]
        keyword = random.choice(keywords)
        self.client.get(f"/feed?search={keyword}", name="/feed?search=")

    @task(1)
    def view_saved(self):
        if not self.is_registered:
            return
        self.client.get("/user/saved", name="/user/saved")

    @task(1)
    def logout_and_back(self):
        if not self.is_registered:
            return
        self._logout()
        self._login()