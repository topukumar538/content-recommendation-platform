from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Feed, UserInteraction, Feedback, CategoryPreference, OTPCode


def get_all_users(db: Session):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "is_blocked": u.is_blocked,
            "created_at": str(u.created_at)
        }
        for u in users
    ]


def toggle_block_user(user_id: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    if user.role == "admin":
        raise ValueError("Cannot block an admin")
    user.is_blocked = not user.is_blocked
    db.commit()
    status = "blocked" if user.is_blocked else "unblocked"
    return {"message": f"User {status} successfully"}


def delete_user(user_id: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    if user.role == "admin":
        raise ValueError("Cannot delete an admin")
    db.query(UserInteraction).filter(UserInteraction.user_id == user_id).delete()
    db.query(CategoryPreference).filter(CategoryPreference.user_id == user_id).delete()
    db.query(Feedback).filter(Feedback.user_id == user_id).delete()
    db.query(OTPCode).filter(OTPCode.email == user.email).delete()
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


def get_stats(db: Session):
    total_users = db.query(User).filter(User.role == "user").count()
    total_posts = db.query(Feed).count()
    total_interactions = db.query(UserInteraction).count()
    total_feedback = db.query(Feedback).count()

    most_liked = db.query(
        Feed.title,
        func.count(UserInteraction.id).label("count")
    ).join(UserInteraction, UserInteraction.feed_id == Feed.id)\
     .filter(UserInteraction.action == "liked")\
     .group_by(Feed.id)\
     .order_by(func.count(UserInteraction.id).desc())\
     .first()

    most_saved = db.query(
        Feed.title,
        func.count(UserInteraction.id).label("count")
    ).join(UserInteraction, UserInteraction.feed_id == Feed.id)\
     .filter(UserInteraction.action == "saved")\
     .group_by(Feed.id)\
     .order_by(func.count(UserInteraction.id).desc())\
     .first()

    return {
        "total_users": total_users,
        "total_posts": total_posts,
        "total_interactions": total_interactions,
        "total_feedback": total_feedback,
        "most_liked_post": most_liked.title if most_liked else None,
        "most_liked_count": most_liked.count if most_liked else 0,
        "most_saved_post": most_saved.title if most_saved else None,
        "most_saved_count": most_saved.count if most_saved else 0,
    }