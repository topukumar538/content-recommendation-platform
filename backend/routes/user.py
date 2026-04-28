from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from core.dependencies import get_db, get_current_user, get_current_active_user
from models import UserInteraction, Feed, User
from schemas.feedback import FeedbackCreate
from services import feedback_service
from schemas.user import ProfileUpdate

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/saved")
def get_saved_posts(db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    interactions = db.query(UserInteraction).filter(
        UserInteraction.user_id == user["user_id"],
        UserInteraction.action == "saved"
    ).all()
    feed_ids = [i.feed_id for i in interactions]
    if not feed_ids:
        return []
    feeds = db.query(Feed).options(
        joinedload(Feed.category),
        joinedload(Feed.author)
    ).filter(Feed.id.in_(feed_ids)).all()
    return [
        {
            "id": f.id,
            "title": f.title,
            "content": f.content,
            "category": f.category.name,
            "author": f.author.username,
            "created_at": str(f.created_at)
        }
        for f in feeds
    ]

@router.delete("/saved/{feed_id}")
def unsave_post(feed_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    interaction = db.query(UserInteraction).filter(
        UserInteraction.user_id == user["user_id"],
        UserInteraction.feed_id == feed_id,
        UserInteraction.action == "saved"
    ).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Saved post not found")
    db.delete(interaction)
    db.commit()
    return {"message": "Post unsaved"}

@router.post("/feedback")
def submit_feedback(data: FeedbackCreate, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    try:
        return feedback_service.submit_feedback(user["user_id"], data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/profile")
def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user)
):
    if not data.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    db_user = db.query(User).filter(User.id == user.id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = data.username.strip()
    db.commit()
    return {"message": "Profile updated successfully"}