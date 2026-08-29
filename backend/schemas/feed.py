from pydantic import BaseModel
from datetime import datetime

class FeedCreate(BaseModel):
    title: str
    content: str
    category_id: int

class FeedUpdate(BaseModel):
    title: str
    content: str
    category_id: int

class FeedResponse(BaseModel):
    id: int
    title: str
    content: str
    category_id: int
    author_id: int
    created_at: datetime

    class Config:
        from_attributes = True

