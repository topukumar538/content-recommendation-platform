from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
from models import User, UserInteraction, Feed, CategoryPreference

ACTION_WEIGHTS = {"viewed": 1, "liked": 3, "saved": 5}

def recalculate_all_scores():
    print("Scheduler: recalculating scores...")
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            update_scores_for_user(user.id, db)
        print(f"Scheduler: updated {len(users)} users")
    except Exception as e:
        print(f"Scheduler error: {e}")
    finally:
        db.close()

from sqlalchemy import func, case

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