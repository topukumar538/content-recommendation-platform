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

def update_scores_for_user(user_id: int, db):
    interactions = db.query(UserInteraction).filter(
        UserInteraction.user_id == user_id
    ).all()
    if not interactions:
        return
    category_scores = {}
    for interaction in interactions:
        feed = db.query(Feed).filter(Feed.id == interaction.feed_id).first()
        if not feed:
            continue
        weight = ACTION_WEIGHTS.get(interaction.action, 0)
        category_scores[feed.category_id] = category_scores.get(feed.category_id, 0) + weight
    total = sum(category_scores.values())
    if total == 0:
        return
    for category_id, score in category_scores.items():
        probability = round(score / total, 4)
        existing = db.query(CategoryPreference).filter(
            CategoryPreference.user_id == user_id,
            CategoryPreference.category_id == category_id
        ).first()
        if existing:
            existing.score = probability
        else:
            db.add(CategoryPreference(
                user_id=user_id,
                category_id=category_id,
                score=probability
            ))
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