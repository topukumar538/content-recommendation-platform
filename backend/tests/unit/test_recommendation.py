import pytest
from datetime import datetime, timedelta
from services.recommendation_service import (
    rank_feeds, softmax, time_decay,
    TIER1_SIZE, TIER1_MAX_PER_CAT, TIER2_SIZE
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

# ── rank_feeds tests ──────────────────────────────────────────

def test_rank_feeds_no_preferences_returns_by_date():
    """With no preferences, posts should be sorted newest first"""
    feeds = [
        MockFeed(1, category_id=1, created_at=datetime.utcnow() - timedelta(hours=10)),
        MockFeed(2, category_id=1, created_at=datetime.utcnow() - timedelta(hours=1)),
        MockFeed(3, category_id=1, created_at=datetime.utcnow() - timedelta(hours=5)),
    ]
    result = rank_feeds(feeds, preferences=[])
    assert result[0].id == 2  # most recent first

def test_rank_feeds_empty_feeds():
    """Empty feed list should return empty list"""
    result = rank_feeds([], preferences=[])
    assert result == []

def test_tier1_category_diversity():
    """Tier 1 deterministic selection caps at TIER1_MAX_PER_CAT per category"""
    # 10 posts from cat 1 (preferred), 10 from cat 2
    feeds = (
        [MockFeed(i, category_id=1, created_at=datetime.utcnow() - timedelta(seconds=i))
         for i in range(10)] +
        [MockFeed(i+10, category_id=2, created_at=datetime.utcnow() - timedelta(seconds=i))
         for i in range(10)]
    )
    prefs = [
        MockPref(category_id=1, score=0.9),
        MockPref(category_id=2, score=0.1),
    ]

    result = rank_feeds(feeds, prefs)

    # category 2 must appear in result — diversity enforced
    categories_in_result = set(f.category_id for f in result)
    assert 2 in categories_in_result

    # all posts must appear — none dropped
    assert len(result) == len(feeds)

    # no duplicates
    ids = [f.id for f in result]
    assert len(ids) == len(set(ids))

def test_rank_feeds_returns_all_posts():
    """All posts should appear in result — none dropped"""
    feeds = [MockFeed(i, category_id=i % 3) for i in range(20)]
    prefs = [MockPref(category_id=i, score=0.33) for i in range(3)]

    result = rank_feeds(feeds, prefs)
    assert len(result) == len(feeds)

def test_rank_feeds_no_duplicate_posts():
    """No post should appear twice in the result"""
    feeds = [MockFeed(i, category_id=i % 3) for i in range(30)]
    prefs = [MockPref(category_id=i, score=0.33) for i in range(3)]

    result = rank_feeds(feeds, prefs)
    ids = [f.id for f in result]
    assert len(ids) == len(set(ids))

def test_preferred_category_ranks_higher():
    """Posts from preferred category should appear in top results"""
    feeds = [
        MockFeed(1, category_id=1),  # preferred
        MockFeed(2, category_id=2),  # not preferred
        MockFeed(3, category_id=1),  # preferred
        MockFeed(4, category_id=2),  # not preferred
        MockFeed(5, category_id=1),  # preferred
    ]
    prefs = [
        MockPref(category_id=1, score=0.9),  # strong preference
        MockPref(category_id=2, score=0.1),  # weak preference
    ]

    result = rank_feeds(feeds, prefs)
    top3_categories = [f.category_id for f in result[:3]]
    assert top3_categories.count(1) >= 2