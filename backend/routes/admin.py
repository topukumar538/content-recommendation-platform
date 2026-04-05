from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.dependencies import get_db, admin_only
from services import admin_service
from services import feedback_service

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), user=Depends(admin_only)):
    return admin_service.get_stats(db)

@router.get("/users")
def get_users(db: Session = Depends(get_db), user=Depends(admin_only)):
    return admin_service.get_all_users(db)

@router.patch("/users/{user_id}/block")
def toggle_block(user_id: int, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        return admin_service.toggle_block_user(user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        return admin_service.delete_user(user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/feedback")
def get_feedback(db: Session = Depends(get_db), user=Depends(admin_only)):
    return feedback_service.get_all_feedback(db)

@router.patch("/feedback/{feedback_id}/resolve")
def resolve_feedback(feedback_id: int, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        return feedback_service.resolve_feedback(feedback_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/feedback/{feedback_id}")
def delete_feedback(feedback_id: int, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        return feedback_service.delete_feedback(feedback_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))