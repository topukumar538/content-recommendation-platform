from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
from models import User, UserInteraction, Feed, CategoryPreference
from sqlalchemy import func, case

ACTION_WEIGHTS = {"viewed": 1, "liked": 3, "saved": 5}

import logging

logger = logging.getLogger(__name__)


def recalculate_all_scores():
    db = SessionLocal()
    try:
        user_ids = [
            row[0] for row in
            db.query(User.id).filter(
                User.is_active == True,      
                User.is_blocked == False,    
            ).all()
        ]
        updated = 0
        for user_id in user_ids:
            try:
                update_scores_for_user(user_id, db)
                updated += 1
            except Exception:
                db.rollback()
                logger.exception("Score update failed for user %s", user_id)
        logger.info("Scheduler: updated %s/%s users", updated, len(user_ids))
    finally:
        db.close()



def update_scores_for_user(user_id: int, db):
    # Single grouped join replaces the previous per-interaction lookup
    # (one query per interaction → one query per user).
    rows = (
        db.query(
            Feed.category_id,
            func.sum(
                case(
                    (UserInteraction.action == "viewed", 1),
                    (UserInteraction.action == "liked", 3),
                    (UserInteraction.action == "saved", 5),
                    else_=0,
                )
            ).label("score"),
        )
        .join(Feed, Feed.id == UserInteraction.feed_id)
        .filter(UserInteraction.user_id == user_id)
        .group_by(Feed.category_id)
        .all()
    )

    category_scores = {cat_id: float(score or 0) for cat_id, score in rows}
    total = sum(category_scores.values())

    # Clear preferences for categories the user no longer interacts with,
    # otherwise stale scores survive forever after an unlike.
    db.query(CategoryPreference).filter(
        CategoryPreference.user_id == user_id,
        ~CategoryPreference.category_id.in_(category_scores.keys() or [-1]),
    ).delete(synchronize_session=False)

    if total == 0:
        db.commit()
        return

    for category_id, score in category_scores.items():
        probability = round(score / total, 4)
        existing = db.query(CategoryPreference).filter(
            CategoryPreference.user_id == user_id,
            CategoryPreference.category_id == category_id,
        ).first()
        if existing:
            existing.score = probability
        else:
            db.add(CategoryPreference(user_id=user_id, category_id=category_id, score=probability))
    db.commit()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        recalculate_all_scores,
        "interval",
        minutes=10,
        misfire_grace_time=60
    )
    scheduler.start()
    print("Scheduler started — recalculates every 10 minutes")
    return scheduler