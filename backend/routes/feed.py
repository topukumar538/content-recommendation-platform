from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from core.dependencies import get_db, admin_only, get_current_active_user
from schemas.feed import FeedCreate, FeedUpdate
from schemas.category import CategoryCreate, CategoryUpdate
from services import feed_service
from models import UserInteraction
from typing import Optional

router = APIRouter(tags=["Feed"])

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = feed_service.get_all_categories(db)
    return [{"id": c.id, "name": c.name} for c in categories]

@router.post("/categories")
def create_category(data: CategoryCreate, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        category = feed_service.create_category(data.name, db)
        return {"id": category.id, "name": category.name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/categories/{category_id}")
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        category = feed_service.update_category(category_id, data.name, db)
        return {"id": category.id, "name": category.name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        return feed_service.delete_category(category_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/feed")
def get_feed(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
    search: Optional[str] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100)
):
    feeds = feed_service.get_personalized_feed(
        user.id,
        db, search, category_id, page, limit
    )
    return {
        "items": [
            {
                "id": f.id,
                "title": f.title,
                "content": f.content,
                "category": f.category.name,
                "category_id": f.category_id,
                "author": f.author.username,
                "created_at": str(f.created_at)
            }
            for f in feeds["items"]
        ],
        "total": feeds["total"],
        "page": feeds["page"],
        "pages": feeds["pages"]
    }

@router.get("/feed/{feed_id}/interactions")
def get_interactions(feed_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    liked = db.query(UserInteraction).filter(
        UserInteraction.user_id == user.id,
        UserInteraction.feed_id == feed_id,
        UserInteraction.action == "liked"
    ).first()
    saved = db.query(UserInteraction).filter(
        UserInteraction.user_id == user.id,
        UserInteraction.feed_id == feed_id,
        UserInteraction.action == "saved"
    ).first()
    return {
        "liked": liked is not None,
        "saved": saved is not None
    }

@router.get("/feed/{feed_id}")
def get_feed_detail(feed_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    try:
        feed = feed_service.get_feed_by_id(feed_id, db)
        feed_service.record_interaction(user.id, feed_id, "viewed", db)
        return {
            "id": feed.id,
            "title": feed.title,
            "content": feed.content,
            "category": feed.category.name,
            "category_id": feed.category_id,
            "author": feed.author.username,
            "created_at": str(feed.created_at)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/feed/{feed_id}/like")
def like_feed(feed_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    try:
        feed_service.get_feed_by_id(feed_id, db)
        result = feed_service.toggle_interaction(user.id, feed_id, "liked", db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/feed/{feed_id}/save")
def save_feed(feed_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    try:
        feed_service.get_feed_by_id(feed_id, db)
        result = feed_service.toggle_interaction(user.id, feed_id, "saved", db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/feed")
def create_feed(data: FeedCreate, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        feed = feed_service.create_feed(data, user.id, db)
        return {"id": feed.id, "title": feed.title, "message": "Post created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/feed/{feed_id}")
def update_feed(feed_id: int, data: FeedUpdate, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        feed = feed_service.update_feed(feed_id, data, db)
        return {"id": feed.id, "title": feed.title, "message": "Post updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/feed/{feed_id}")
def delete_feed(feed_id: int, db: Session = Depends(get_db), user=Depends(admin_only)):
    try:
        return feed_service.delete_feed(feed_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))