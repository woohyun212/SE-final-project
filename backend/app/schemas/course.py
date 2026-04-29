from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    professor: Optional[str] = None
    credits: int = Field(default=3, ge=1, le=4)
    semester: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    professor: Optional[str] = None
    credits: Optional[int] = Field(default=None, ge=1, le=4)
    semester: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None

class CourseResponse(CourseBase):
    id: int
    user_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}
