import math
import random
from datetime import datetime
from collections import defaultdict

# ===== config =====
FEED_LIMIT          = 500
TIER1_SIZE          = 15
TIER1_MAX_PER_CAT   = 3
TIER2_SIZE          = 5
SOFTMAX_TEMPERATURE = 0.7
EPSILON             = 0.1
PREF_WEIGHT         = 0.7
FRESH_WEIGHT        = 0.3
BASE_SCORE          = 0.1
TIME_DECAY_HOURS    = 24


def softmax(scores, temperature=SOFTMAX_TEMPERATURE):
    scaled = [s / temperature for s in scores]
    m      = max(scaled)
    exps   = [math.exp(s - m) for s in scaled]
    total  = sum(exps)
    return [e / total for e in exps]


def time_decay(created_at):
    hours = (datetime.utcnow() - created_at.replace(tzinfo=None)).total_seconds() / 3600
    return math.exp(-hours / TIME_DECAY_HOURS)


# ============================================================
# Recommendation Engine — Complexity Analysis
# ============================================================
# Input:
#   all_feeds   → F posts (max 500, controlled by FEED_LIMIT)
#   preferences → C category scores for this user
#
# Overall: O(F log F) time, O(F) space
# ============================================================

def rank_feeds(all_feeds, preferences):
    if not preferences:
        # O(F log F) — sort by date, no preferences yet
        return sorted(all_feeds, key=lambda f: f.created_at, reverse=True)

    # O(C) — build hashmap for O(1) category lookup
    pref_map = {p.category_id: p.score for p in preferences}

    # O(F) — score every post once
    raw = {}
    for f in all_feeds:
        preference = pref_map.get(f.category_id, 0)  # O(1) hashmap lookup
        freshness  = time_decay(f.created_at)          # O(1) math.exp()
        raw[f.id]  = (PREF_WEIGHT * preference) + (FRESH_WEIGHT * freshness) + BASE_SCORE

    # O(F log F) — sort all posts by combined score
    top_posts = sorted(all_feeds, key=lambda f: raw[f.id], reverse=True)

    result    = []
    seen_ids  = set()        # O(1) lookup
    cat_count = defaultdict(int)

    # TIER 1 — O(F) worst case, stops at TIER1_SIZE
    # Deterministic top scored posts with category diversity cap
    for feed in top_posts:
        if len(result) == TIER1_SIZE:
            break
        if cat_count[feed.category_id] == TIER1_MAX_PER_CAT:
            continue
        result.append(feed)
        seen_ids.add(feed.id)
        cat_count[feed.category_id] += 1

    # TIER 2 — O(F) to build pool, O(T2) softmax weighted sampling
    # Probabilistic exploration — high score = more likely, not guaranteed
    remaining_pool = [f for f in all_feeds if f.id not in seen_ids]
    if remaining_pool:
        pool_scores = [raw[f.id] for f in remaining_pool]
        weights     = softmax(pool_scores)   # O(F) — exp() per post
        candidates  = random.choices(remaining_pool, weights=weights, k=TIER2_SIZE)
        added = 0
        for feed in candidates:
            if feed.id not in seen_ids and added < TIER2_SIZE:
                result.append(feed)
                seen_ids.add(feed.id)
                added += 1

    # EPSILON GREEDY — O(F) to find unseen posts
    # 10% chance of truly random post — breaks filter bubble
    if random.random() < EPSILON:
        unseen = [f for f in all_feeds if f.id not in seen_ids]
        if unseen:
            random_post = random.choice(unseen)  # O(1)
            result.append(random_post)
            seen_ids.add(random_post.id)

    # TIER 3 — O(F log F) sort by date, O(F) iteration
    # Newest unseen posts — ensures fresh content always discoverable
    by_date = sorted(all_feeds, key=lambda f: f.created_at, reverse=True)
    for feed in by_date:
        if feed.id not in seen_ids:
            result.append(feed)
            seen_ids.add(feed.id)

    return result