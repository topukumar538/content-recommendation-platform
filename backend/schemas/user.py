from pydantic import BaseModel

class ProfileUpdate(BaseModel):
    username: str