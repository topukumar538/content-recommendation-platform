from sqlalchemy.orm import Session, joinedload
from models import Feed, Category, UserInteraction, CategoryPreference
from schemas.feed import FeedCreate, FeedUpdate
import math
import random
from datetime import datetime
from collections import defaultdict

ACTION_WEIGHTS = {"viewed": 1, "liked": 3, "saved": 5}

def get_all_categories(db: Session):
    return db.query(Category).all()

def create_category(name: str, db: Session):
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        raise ValueError("Category already exists")
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

def update_category(category_id: int, name: str, db: Session):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise ValueError("Category not found")
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        raise ValueError("Category name already exists")
    category.name = name
    db.commit()
    db.refresh(category)
    return category

def delete_category(category_id: int, db: Session):
    posts_count = db.query(Feed).filter(Feed.category_id == category_id).count()
    if posts_count > 0:
        raise ValueError(f"Cannot delete — {posts_count} post(s) use this category")
    db.query(CategoryPreference).filter(CategoryPreference.category_id == category_id).delete()
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise ValueError("Category not found")
    db.delete(category)
    db.commit()
    return {"message": "Category deleted"}


# Recommendation config
FEED_LIMIT          = 500   # max posts to fetch from db
TIER1_SIZE          = 15    # top scored posts
TIER1_MAX_PER_CAT   = 3     # max posts per category in tier 1
TIER2_SIZE          = 5     # softmax wildcard posts
SOFTMAX_TEMPERATURE = 0.7   # exploration sharpness
EPSILON             = 0.1   # random exploration probability
PREF_WEIGHT         = 0.7   # preference score weight
FRESH_WEIGHT        = 0.3   # freshness score weight
BASE_SCORE          = 0.1   # prevents zero probability
TIME_DECAY_HOURS    = 24    # freshness decay over N hours

def softmax(scores, temperature=SOFTMAX_TEMPERATURE):
    scaled = [s / temperature for s in scores]
    m      = max(scaled)
    exps   = [math.exp(s - m) for s in scaled]
    total  = sum(exps)
    return [e / total for e in exps]

def time_decay(created_at):
    hours = (datetime.utcnow() - created_at.replace(tzinfo=None)).total_seconds() / 3600
    return math.exp(-hours / TIME_DECAY_HOURS)

def get_personalized_feed(user_id: int, db: Session, search: str, category_id):
    query = db.query(Feed).options(
        joinedload(Feed.category),
        joinedload(Feed.author)
    )
    if search:
        query = query.filter(
            Feed.title.ilike(f"%{search}%") |
            Feed.content.ilike(f"%{search}%")
        )
    if category_id:
        query = query.filter(Feed.category_id == category_id)

    all_feeds = query.limit(FEED_LIMIT).all()

    if not all_feeds:
        return []

    preferences = db.query(CategoryPreference).filter(
        CategoryPreference.user_id == user_id
    ).all()

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

    result   = []
    seen_ids = set()
    cat_count = defaultdict(int)

    # TIER 1 — top scored posts with category diversity
    top_posts = sorted(all_feeds, key=lambda f: raw[f.id], reverse=True)
    for feed in top_posts:
        if len(result) == TIER1_SIZE:
            break
        if cat_count[feed.category_id] == TIER1_MAX_PER_CAT:
            continue
        result.append(feed)
        seen_ids.add(feed.id)
        cat_count[feed.category_id] += 1

    # TIER 2 — softmax weighted wildcard posts
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

    # epsilon greedy — true random exploration
    if random.random() < EPSILON:
        unseen = [f for f in all_feeds if f.id not in seen_ids]
        if unseen:
            random_post = random.choice(unseen)
            result.append(random_post)
            seen_ids.add(random_post.id)

    # TIER 3 — newest unseen posts
    by_date = sorted(all_feeds, key=lambda f: f.created_at, reverse=True)
    for feed in by_date:
        if feed.id not in seen_ids:
            result.append(feed)
            seen_ids.add(feed.id)

    return result


def get_feed_by_id(feed_id: int, db: Session):
    feed = db.query(Feed).options(
        joinedload(Feed.category),
        joinedload(Feed.author)
    ).filter(Feed.id == feed_id).first()
    if not feed:
        raise ValueError("Post not found")
    return feed

def create_feed(data: FeedCreate, author_id: int, db: Session):
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise ValueError("Category not found")
    feed = Feed(
        title=data.title,
        content=data.content,
        category_id=data.category_id,
        author_id=author_id
    )
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return feed

def update_feed(feed_id: int, data: FeedUpdate, db: Session):
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise ValueError("Post not found")
    feed.title = data.title
    feed.content = data.content
    feed.category_id = data.category_id
    db.commit()
    db.refresh(feed)
    return feed

def delete_feed(feed_id: int, db: Session):
    db.query(UserInteraction).filter(UserInteraction.feed_id == feed_id).delete()
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise ValueError("Post not found")
    db.delete(feed)
    db.commit()
    return {"message": "Post deleted"}

def record_interaction(user_id: int, feed_id: int, action: str, db: Session):
    existing = db.query(UserInteraction).filter(
        UserInteraction.user_id == user_id,
        UserInteraction.feed_id == feed_id,
        UserInteraction.action == action
    ).first()
    if not existing:
        db.add(UserInteraction(user_id=user_id, feed_id=feed_id, action=action))
        db.commit()
        # removed instant score update — scheduler handles this every 10 minutes
