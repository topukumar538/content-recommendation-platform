import math
import random
from datetime import datetime, timezone
from collections import defaultdict

# ===== config =====
FEED_LIMIT          = 500
BUCKET_SIZE         = 20

# Slot budget within one bucket. Sums to BUCKET_SIZE.
SLOT_TOP            = 5    # highest scoring, category capped
SLOT_WEIGHTED       = 8    # softmax sampled
SLOT_RANDOM         = 2    # uniform random, ignores score
SLOT_NEWEST         = 3    # most recent by date
SLOT_RECYCLED       = 2    # already viewed, shown again

TOP_MAX_PER_CAT     = 3
SOFTMAX_TEMPERATURE = 0.7
PREF_WEIGHT         = 0.7
FRESH_WEIGHT        = 0.3
BASE_SCORE          = 0.1
TIME_DECAY_HOURS    = 24   # time constant of exp(-t/24h); half-life is 24*ln2 ~ 16.6h
RECYCLE_POOL_LIMIT  = 100   # how far back the recycle slot reaches


def softmax(scores, temperature=SOFTMAX_TEMPERATURE):
    scaled = [s / temperature for s in scores]
    m      = max(scaled)
    exps   = [math.exp(s - m) for s in scaled]
    total  = sum(exps)
    return [e / total for e in exps]


def time_decay(created_at, now=None):
    # Columns are DateTime(timezone=True), but SQLite (tests) hands back naive
    # datetimes. Assume UTC when naive, convert when aware -- .replace(tzinfo=None)
    # would silently drop the offset instead of converting it.
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    hours = (now - created_at).total_seconds() / 3600
    return math.exp(-hours / TIME_DECAY_HOURS)


# ============================================================
# Recommendation Engine
# ============================================================
# The whole ordering is built in ONE pass, in buckets of BUCKET_SIZE.
#
# The previous version re-ran on every request and re-rolled its random
# tiers each time, so page 2 was sliced out of a different ordering than
# page 1 had been: posts appeared twice and others were never reachable.
# Building every bucket up front against a single seen set means page N is
# genuinely the Nth slice of one stable list -- but only if the caller
# passes a stable `seed`. Without one the sampling re-rolls per request and
# the bug returns.
#
# Input:
#   candidates   -> F unseen posts (capped by FEED_LIMIT)
#   preferences  -> C category scores
#   viewed       -> posts already read, for the recycle slot
#
# O(F log F) time, O(F) space
# ============================================================

def rank_feeds(candidates, preferences, viewed=None, seed=None):
    if not candidates:
        return []

    if not preferences:
        # No history yet -- nothing to personalise against.
        return sorted(candidates, key=lambda f: f.created_at, reverse=True)

    viewed = list(viewed or [])
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)

    # O(C) -- hashmap for O(1) category lookup
    pref_map = {p.category_id: p.score for p in preferences}

    # O(F) -- score every post once
    raw = {}
    for f in candidates:
        preference = pref_map.get(f.category_id, 0)
        freshness  = time_decay(f.created_at, now)
        raw[f.id]  = (PREF_WEIGHT * preference) + (FRESH_WEIGHT * freshness) + BASE_SCORE

    by_score     = sorted(candidates, key=lambda f: raw[f.id], reverse=True)
    by_date      = sorted(candidates, key=lambda f: f.created_at, reverse=True)
    recycle_pool = sorted(viewed, key=lambda f: f.created_at, reverse=True)

    result   = []
    seen_ids = set()

    def take(feed):
        result.append(feed)
        seen_ids.add(feed.id)

    def available(pool):
        return [f for f in pool if f.id not in seen_ids]

    n_buckets = math.ceil(len(candidates) / BUCKET_SIZE)

    for _ in range(n_buckets):
        # --- top: best scoring, capped per category ----------------------
        # Without the cap a user with one dominant interest sees only that
        # category here, and the exploration slots below never get to
        # counteract a monopoly that starts at the top of every page.
        cat_count = defaultdict(int)
        filled = 0
        for feed in by_score:
            if filled == SLOT_TOP:
                break
            if feed.id in seen_ids:
                continue
            if cat_count[feed.category_id] == TOP_MAX_PER_CAT:
                continue
            take(feed)
            cat_count[feed.category_id] += 1
            filled += 1

        # --- weighted: softmax sampling without replacement ---------------
        # Scores sit in a narrow band, so posts a few ranks apart are often
        # near-identical in quality. Sampling lets those near-ties actually
        # swap instead of being frozen by a strict sort.
        #
        # random.choices samples WITH replacement, so one call with k=n can
        # return duplicates and yield fewer than n distinct posts. Drawing
        # one at a time and removing the pick guarantees distinct results.
        pool = available(by_score)
        if pool:
            weights = list(softmax([raw[f.id] for f in pool]))
            pool = list(pool)
            added = 0
            while pool and added < SLOT_WEIGHTED:
                pick = rng.choices(pool, weights=weights, k=1)[0]
                idx  = pool.index(pick)
                pool.pop(idx)
                weights.pop(idx)
                take(pick)
                added += 1

        # --- random: ignores score entirely -------------------------------
        # The only route by which a category the user has never touched can
        # reach them, since it has no preference score to rank on.
        pool = available(by_score)
        for _ in range(min(SLOT_RANDOM, len(pool))):
            pick = rng.choice(pool)
            pool.remove(pick)
            take(pick)

        # --- newest: recency regardless of preference ----------------------
        for feed in available(by_date)[:SLOT_NEWEST]:
            take(feed)

        # --- recycled: something they read a while back --------------------
        # Runs dry once the viewed pool is exhausted; the backfill below
        # then uses the slot for fresh posts rather than returning short.
        for feed in [f for f in recycle_pool if f.id not in seen_ids][:SLOT_RECYCLED]:
            take(feed)

        # --- backfill ------------------------------------------------------
        # Any slot type that ran dry leaves the bucket short. Top up by score
        # so a bucket is always BUCKET_SIZE long while candidates remain.
        want = BUCKET_SIZE - (len(result) % BUCKET_SIZE or BUCKET_SIZE)
        if want != BUCKET_SIZE:
            for feed in by_score:
                if want == 0:
                    break
                if feed.id in seen_ids:
                    continue
                take(feed)
                want -= 1

    # Anything left over -- e.g. skipped by the category cap in every
    # bucket -- is appended by score so no candidate is unreachable.
    for feed in by_score:
        if feed.id not in seen_ids:
            take(feed)

    return result