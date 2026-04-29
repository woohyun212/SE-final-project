from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate

class CourseService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_courses(self, user_id: int) -> List[Course]:
        return self.db.query(Course).filter(Course.user_id == user_id).all()
    
    def get_course(self, user_id: int, course_id: int) -> Optional[Course]:
        return self.db.query(Course).filter(Course.user_id == user_id, Course.id == course_id).first()
    
    def create_course(self, user_id: int, data: CourseCreate) -> Course:
        course = Course(user_id=user_id, **data.model_dump())
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course
    
    def update_course(self, user_id: int, course_id: int, data: CourseUpdate) -> Optional[Course]:
        course = self.get_course(user_id, course_id)
        if not course:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(course, key, value)
        self.db.commit()
        self.db.refresh(course)
        return course
    
    def delete_course(self, user_id: int, course_id: int) -> bool:
        course = self.get_course(user_id, course_id)
        if not course:
            return False
        self.db.delete(course)
        self.db.commit()
        return True
