from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    grade: Optional[float] = Field(default=None, ge=0, le=100)
    is_completed: bool = False

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    grade: Optional[float] = Field(default=None, ge=0, le=100)
    is_completed: Optional[bool] = None

class AssignmentResponse(AssignmentBase):
    id: int
    course_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}
