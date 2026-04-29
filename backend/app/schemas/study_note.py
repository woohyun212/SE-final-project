from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class StudyNoteBase(BaseModel):
    title: str
    content: Optional[str] = None

class StudyNoteCreate(StudyNoteBase):
    pass

class StudyNoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class StudyNoteResponse(StudyNoteBase):
    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
