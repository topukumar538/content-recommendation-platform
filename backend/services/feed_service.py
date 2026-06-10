from sqlalchemy.orm import Session, joinedload
from models import Feed, Category, UserInteraction, CategoryPreference
from schemas.feed import FeedCreate, FeedUpdate
from services.recommendation_service import rank_feeds, FEED_LIMIT
import math
from sqlalchemy.exc import IntegrityError



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


def get_personalized_feed(user_id: int, db: Session, search: str, category_id, page: int = 1, limit: int = 20):
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
        return {"items": [], "total": 0, "page": page, "pages": 0}

    preferences = db.query(CategoryPreference).filter(
        CategoryPreference.user_id == user_id
    ).all()

    ranked = rank_feeds(all_feeds, preferences)

    # pagination happens AFTER ranking
    total  = len(ranked)
    pages  = math.ceil(total / limit)
    offset = (page - 1) * limit
    items  = ranked[offset : offset + limit]

    return {"items": items, "total": total, "page": page, "pages": pages}


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
    try:
        db.add(UserInteraction(user_id=user_id, feed_id=feed_id, action=action))
        db.commit()
    except IntegrityError:
        db.rollback()  # duplicate — silently ignore

def toggle_interaction(user_id: int, feed_id: int, action: str, db: Session):
    existing = db.query(UserInteraction).filter(
        UserInteraction.user_id == user_id,
        UserInteraction.feed_id == feed_id,
        UserInteraction.action == action
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"action": "removed", "status": False}
    else:
        db.add(UserInteraction(user_id=user_id, feed_id=feed_id, action=action))
        db.commit()
        return {"action": "added", "status": True}