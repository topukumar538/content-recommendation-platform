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


def rank_feeds(all_feeds, preferences):
    if not preferences:
        return sorted(all_feeds, key=lambda f: f.created_at, reverse=True)

    pref_map = {p.category_id: p.score for p in preferences}

    raw = {}
    for f in all_feeds:
        preference = pref_map.get(f.category_id, 0)
        freshness  = time_decay(f.created_at)
        raw[f.id]  = (PREF_WEIGHT * preference) + (FRESH_WEIGHT * freshness) + BASE_SCORE

    max_score = max(raw.values()) or 1
    if max_score == 0:
        return sorted(all_feeds, key=lambda f: f.created_at, reverse=True)

    result    = []
    seen_ids  = set()
    cat_count = defaultdict(int)

    # TIER 1 — top scored with category diversity
    top_posts = sorted(all_feeds, key=lambda f: raw[f.id], reverse=True)
    for feed in top_posts:
        if len(result) == TIER1_SIZE:
            break
        if cat_count[feed.category_id] == TIER1_MAX_PER_CAT:
            continue
        result.append(feed)
        seen_ids.add(feed.id)
        cat_count[feed.category_id] += 1

    # TIER 2 — softmax weighted wildcard
    remaining_pool = [f for f in all_feeds if f.id not in seen_ids]
    if remaining_pool:
        pool_scores = [raw[f.id] for f in remaining_pool]
        weights     = softmax(pool_scores)
        candidates  = random.choices(remaining_pool, weights=weights, k=TIER2_SIZE)
        added = 0
        for feed in candidates:
            if feed.id not in seen_ids and added < TIER2_SIZE:
                result.append(feed)
                seen_ids.add(feed.id)
                added += 1

    # epsilon greedy — true random
    if random.random() < EPSILON:
        unseen = [f for f in all_feeds if f.id not in seen_ids]
        if unseen:
            random_post = random.choice(unseen)
            result.append(random_post)
            seen_ids.add(random_post.id)

    # TIER 3 — newest unseen
    by_date = sorted(all_feeds, key=lambda f: f.created_at, reverse=True)
    for feed in by_date:
        if feed.id not in seen_ids:
            result.append(feed)
            seen_ids.add(feed.id)

    return result