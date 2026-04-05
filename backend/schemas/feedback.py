from pydantic import BaseModel
from datetime import datetime

class FeedbackCreate(BaseModel):
    message: str
    rating: int

class FeedbackResponse(BaseModel):
    id: int
    message: str
    rating: int
    is_resolved: bool
    created_at: datetime
    username: str

    class Config:
        from_attributes = True