from sqlalchemy.orm import Session
from models import Feedback
from schemas.feedback import FeedbackCreate

def submit_feedback(user_id: int, data: FeedbackCreate, db: Session):
    if not 1 <= data.rating <= 5:
        raise ValueError("Rating must be between 1 and 5")
    if not data.message.strip():
        raise ValueError("Message cannot be empty")
    feedback = Feedback(
        user_id=user_id,
        message=data.message,
        rating=data.rating
    )
    db.add(feedback)
    db.commit()
    return {"message": "Feedback submitted successfully"}

def get_all_feedback(db: Session):
    feedbacks = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
    return [
        {
            "id": f.id,
            "message": f.message,
            "rating": f.rating,
            "is_resolved": f.is_resolved,
            "created_at": str(f.created_at),
            "username": f.user.username,
            "email": f.user.email
        }
        for f in feedbacks
    ]

def resolve_feedback(feedback_id: int, db: Session):
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise ValueError("Feedback not found")
    feedback.is_resolved = not feedback.is_resolved
    db.commit()
    return {"message": "Updated", "is_resolved": feedback.is_resolved}

def delete_feedback(feedback_id: int, db: Session):
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise ValueError("Feedback not found")
    db.delete(feedback)
    db.commit()
    return {"message": "Feedback deleted"}