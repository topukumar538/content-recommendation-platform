"""
Unit tests for the scheduler's normalisation step.

These cover normalize_batch only -- the part between the aggregate query
and the two write statements. The statements themselves cannot run here:
tuple_(...).notin_() is PostgreSQL-only and the test database is SQLite.
The action weights and the 30-day decay are applied in SQL, so `rows`
arrives already aggregated and those are not covered either.
"""

import pytest

from scheduler import normalize_batch


def scores_for(values, user_id):
    """{category_id: score} for one user, out of the VALUES list."""
    return {v["category_id"]: v["score"] for v in values if v["user_id"] == user_id}


# ── normalisation ─────────────────────────────────────────────

def test_shares_sum_to_one():
    """Preferences are probabilities -- a user's shares must sum to 1."""
    rows = [(1, 10, 6.0), (1, 20, 3.0), (1, 30, 1.0)]
    values, _ = normalize_batch([1], rows)
    assert sum(scores_for(values, 1).values()) == pytest.approx(1.0, abs=1e-3)


def test_shares_are_proportional():
    """Twice the raw weight means twice the share."""
    rows = [(1, 10, 8.0), (1, 20, 4.0)]
    values, _ = normalize_batch([1], rows)
    scores = scores_for(values, 1)
    assert scores[10] == pytest.approx(2 * scores[20], rel=1e-3)


def test_each_user_normalised_independently():
    """A heavy user must not shrink a light user's shares. Both are
    normalised against their own total, not the batch total."""
    rows = [(1, 10, 100.0), (2, 10, 0.5), (2, 20, 0.5)]
    values, _ = normalize_batch([1, 2], rows)
    assert scores_for(values, 1)[10] == pytest.approx(1.0, abs=1e-3)
    assert sum(scores_for(values, 2).values()) == pytest.approx(1.0, abs=1e-3)


def test_scores_rounded_to_four_places():
    """The column stores 4 decimal places; rounding happens here."""
    rows = [(1, 10, 1.0), (1, 20, 1.0), (1, 30, 1.0)]
    values, _ = normalize_batch([1], rows)
    for v in values:
        assert v["score"] == round(v["score"], 4)


# ── the dormant-user guard ────────────────────────────────────

def test_fully_decayed_user_produces_nothing():
    """Every interaction decayed to near zero. Dividing by that total is
    meaningless, so the user is skipped entirely rather than written with
    a fabricated share."""
    rows = [(1, 10, 1e-12), (1, 20, 1e-13)]
    values, keep = normalize_batch([1], rows)
    assert values == []
    assert keep == set()


def test_skipped_user_is_absent_from_keep():
    """A skipped user contributes no pairs to `keep`, which is what makes
    the scoped delete clear their now-meaningless stored preferences."""
    rows = [(1, 10, 5.0), (2, 20, 1e-12)]
    _, keep = normalize_batch([1, 2], rows)
    assert (1, 10) in keep
    assert not any(user_id == 2 for user_id, _ in keep)


def test_user_with_no_interactions_is_skipped():
    """A user in the batch with no rows at all -- same path as a fully
    decayed one: no write, no keep, stale preferences deleted."""
    values, keep = normalize_batch([1, 2], [(1, 10, 5.0)])
    assert scores_for(values, 2) == {}
    assert not any(user_id == 2 for user_id, _ in keep)


def test_null_score_treated_as_zero():
    """SUM() returns NULL, not 0, when nothing matches the CASE."""
    rows = [(1, 10, None), (1, 20, 4.0)]
    values, _ = normalize_batch([1], rows)
    scores = scores_for(values, 1)
    assert scores[10] == 0.0
    assert scores[20] == pytest.approx(1.0, abs=1e-3)


# ── keep / values agreement ───────────────────────────────────

def test_keep_matches_values_exactly():
    """Every written pair must survive the delete, and nothing else may.
    A mismatch either wipes a row that was just written or leaves a stale
    one behind."""
    rows = [(1, 10, 2.0), (1, 20, 3.0), (2, 10, 1.0)]
    values, keep = normalize_batch([1, 2], rows)
    assert {(v["user_id"], v["category_id"]) for v in values} == keep


def test_rows_for_users_outside_the_batch_are_ignored():
    """The delete is scoped to user_ids. A pair from outside that scope
    landing in `keep` would be harmless, but a value would be written for
    a user this batch never claimed to score."""
    rows = [(1, 10, 2.0), (99, 10, 5.0)]
    values, keep = normalize_batch([1], rows)
    assert all(v["user_id"] == 1 for v in values)
    assert all(user_id == 1 for user_id, _ in keep)


def test_empty_batch():
    assert normalize_batch([], []) == ([], set())