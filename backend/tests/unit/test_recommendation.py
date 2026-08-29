import pytest
from datetime import datetime, timedelta

from services.recommendation_service import (
    rank_feeds, softmax, time_decay,
    BUCKET_SIZE, SLOT_TOP, SLOT_WEIGHTED, TOP_MAX_PER_CAT,
)

# ── helpers ──────────────────────────────────────────────────

class MockFeed:
    """Fake Feed object for testing without DB"""
    def __init__(self, id, category_id, created_at=None):
        self.id          = id
        self.category_id = category_id
        self.created_at  = created_at or datetime.utcnow()

class MockPref:
    """Fake CategoryPreference object for testing without DB"""
    def __init__(self, category_id, score):
        self.category_id = category_id
        self.score       = score

# ── softmax tests ─────────────────────────────────────────────

def test_softmax_sums_to_one():
    """Softmax probabilities must always sum to 1.0"""
    scores = [0.8, 0.5, 0.2, 0.1]
    result = softmax(scores)
    assert abs(sum(result) - 1.0) < 1e-6

def test_softmax_higher_score_higher_probability():
    """Higher score must get higher probability"""
    scores = [0.8, 0.5, 0.2]
    result = softmax(scores)
    assert result[0] > result[1] > result[2]

def test_softmax_single_item():
    """Single item must get probability 1.0"""
    result = softmax([0.5])
    assert abs(result[0] - 1.0) < 1e-6

# ── time decay tests ──────────────────────────────────────────

def test_time_decay_fresh_post():
    """Post just created should have freshness close to 1.0"""
    now = datetime.utcnow()
    score = time_decay(now)
    assert score > 0.99

def test_time_decay_old_post():
    """Post from 72 hours ago should have low freshness"""
    old = datetime.utcnow() - timedelta(hours=72)
    score = time_decay(old)
    assert score < 0.1

def test_time_decay_never_zero():
    """Freshness should never reach zero — asymptotic decay"""
    very_old = datetime.utcnow() - timedelta(days=365)
    score = time_decay(very_old)
    assert score > 0

def test_time_decay_decreases_over_time():
    """Older posts must have lower freshness than newer posts"""
    new_post = datetime.utcnow() - timedelta(hours=1)
    old_post = datetime.utcnow() - timedelta(hours=48)
    assert time_decay(new_post) > time_decay(old_post)

# ── rank_feeds: basics ────────────────────────────────────────

def test_rank_feeds_no_preferences_returns_by_date():
    """With no preferences there is nothing to personalise against, so the
    ordering falls back to newest first."""
    feeds = [
        MockFeed(1, category_id=1, created_at=datetime.utcnow() - timedelta(hours=10)),
        MockFeed(2, category_id=1, created_at=datetime.utcnow() - timedelta(hours=1)),
        MockFeed(3, category_id=1, created_at=datetime.utcnow() - timedelta(hours=5)),
    ]
    result = rank_feeds(feeds, preferences=[])
    assert result[0].id == 2

def test_rank_feeds_empty_feeds():
    """Empty candidate list should return empty list"""
    assert rank_feeds([], preferences=[]) == []

def test_rank_feeds_returns_all_posts():
    """Every candidate must appear — none silently dropped"""
    feeds = [MockFeed(i, category_id=i % 3) for i in range(20)]
    prefs = [MockPref(category_id=i, score=0.33) for i in range(3)]
    result = rank_feeds(feeds, prefs, seed=1)
    assert {f.id for f in feeds} <= {f.id for f in result}

def test_rank_feeds_no_duplicate_posts():
    """No post may appear twice, in one bucket or across buckets"""
    feeds = [MockFeed(i, category_id=i % 3) for i in range(30)]
    prefs = [MockPref(category_id=i, score=0.33) for i in range(3)]
    result = rank_feeds(feeds, prefs, seed=1)
    ids = [f.id for f in result]
    assert len(ids) == len(set(ids))

# ── rank_feeds: pagination stability ──────────────────────────

def test_same_seed_gives_same_order():
    """The property pagination depends on. rank_feeds samples in its
    weighted and random slots, so without a fixed seed page 2 would be
    sliced out of an ordering page 1 never came from -- repeating some
    posts and hiding others."""
    feeds = [MockFeed(i, category_id=i % 4) for i in range(60)]
    prefs = [MockPref(category_id=i, score=0.25) for i in range(4)]
    a = [f.id for f in rank_feeds(feeds, prefs, seed=7)]
    b = [f.id for f in rank_feeds(feeds, prefs, seed=7)]
    assert a == b

def test_different_seed_reshuffles():
    """Rotating the seed hourly is what makes the feed feel new on a
    return visit, so a different seed must actually change the order."""
    feeds = [MockFeed(i, category_id=i % 4) for i in range(60)]
    prefs = [MockPref(category_id=i, score=0.25) for i in range(4)]
    a = [f.id for f in rank_feeds(feeds, prefs, seed=7)]
    c = [f.id for f in rank_feeds(feeds, prefs, seed=8)]
    assert a != c

# ── rank_feeds: diversity ─────────────────────────────────────

def test_top_slots_capped_per_category():
    """Without the cap a user with one dominant interest sees only that
    category at the top of every bucket, and the exploration slots never
    get to counteract a monopoly that starts there."""
    feeds = (
        [MockFeed(i, category_id=1) for i in range(10)] +
        [MockFeed(i + 10, category_id=2) for i in range(10)]
    )
    prefs = [MockPref(category_id=1, score=0.9), MockPref(category_id=2, score=0.1)]

    result = rank_feeds(feeds, prefs, seed=1)

    counts = {}
    for f in result[:SLOT_TOP]:
        counts[f.category_id] = counts.get(f.category_id, 0) + 1
    assert max(counts.values()) <= TOP_MAX_PER_CAT

def test_weak_category_still_reachable():
    """A barely-preferred category must still surface somewhere."""
    feeds = (
        [MockFeed(i, category_id=1) for i in range(10)] +
        [MockFeed(i + 10, category_id=2) for i in range(10)]
    )
    prefs = [MockPref(category_id=1, score=0.9), MockPref(category_id=2, score=0.1)]
    result = rank_feeds(feeds, prefs, seed=1)
    assert 2 in {f.category_id for f in result}

def test_preferred_category_ranks_higher():
    """Posts from the preferred category should dominate the top slots"""
    feeds = [
        MockFeed(1, category_id=1),
        MockFeed(2, category_id=2),
        MockFeed(3, category_id=1),
        MockFeed(4, category_id=2),
        MockFeed(5, category_id=1),
    ]
    prefs = [MockPref(category_id=1, score=0.9), MockPref(category_id=2, score=0.1)]
    result = rank_feeds(feeds, prefs, seed=1)
    assert [f.category_id for f in result[:3]].count(1) >= 2

# ── rank_feeds: recycled slot ─────────────────────────────────

def test_viewed_posts_recycled():
    """Already-read posts fill the recycle slots, so a user who has run
    low on fresh content still gets a full bucket."""
    feeds  = [MockFeed(i, category_id=i % 3) for i in range(40)]
    viewed = [MockFeed(100 + i, category_id=1) for i in range(6)]
    prefs  = [MockPref(category_id=i, score=0.33) for i in range(3)]

    result = rank_feeds(feeds, prefs, viewed=viewed, seed=1)
    recycled_ids = {f.id for f in viewed}
    assert recycled_ids & {f.id for f in result}

def test_no_viewed_posts_still_works():
    """The recycle pool runs dry once a user's history is exhausted; the
    bucket must backfill rather than return short."""
    feeds = [MockFeed(i, category_id=i % 3) for i in range(40)]
    prefs = [MockPref(category_id=i, score=0.33) for i in range(3)]
    result = rank_feeds(feeds, prefs, viewed=[], seed=1)
    assert len(result) >= len(feeds)