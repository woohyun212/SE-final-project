from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.assignment import Assignment
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate

class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_assignments(self, course_id: int) -> List[Assignment]:
        return self.db.query(Assignment).filter(Assignment.course_id == course_id).all()
    
    def get_assignment(self, course_id: int, assignment_id: int) -> Optional[Assignment]:
        return self.db.query(Assignment).filter(
            Assignment.course_id == course_id,
            Assignment.id == assignment_id
        ).first()
    
    def create_assignment(self, course_id: int, data: AssignmentCreate) -> Assignment:
        assignment = Assignment(course_id=course_id, **data.model_dump())
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment
    
    def update_assignment(self, course_id: int, assignment_id: int, data: AssignmentUpdate) -> Optional[Assignment]:
        assignment = self.get_assignment(course_id, assignment_id)
        if not assignment:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(assignment, key, value)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment
    
    def delete_assignment(self, course_id: int, assignment_id: int) -> bool:
        assignment = self.get_assignment(course_id, assignment_id)
        if not assignment:
            return False
        self.db.delete(assignment)
        self.db.commit()
        return True
