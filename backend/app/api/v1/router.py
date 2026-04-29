from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from app.api.v1.endpoints import auth, courses, assignments, study_notes
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.assignment import Assignment
from app.models.course import Course

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(courses.router)
router.include_router(assignments.router)
router.include_router(study_notes.router)

@router.get("/stats", tags=["통계"])
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_courses = db.query(Course).filter(Course.user_id == current_user.id).count()
    
    user_course_ids = [c.id for c in db.query(Course).filter(Course.user_id == current_user.id).all()]
    
    total_assignments = db.query(Assignment).filter(Assignment.course_id.in_(user_course_ids)).count() if user_course_ids else 0
    completed_assignments = db.query(Assignment).filter(
        Assignment.course_id.in_(user_course_ids),
        Assignment.is_completed == True
    ).count() if user_course_ids else 0
    
    now = datetime.utcnow()
    upcoming_assignments = db.query(Assignment).filter(
        Assignment.course_id.in_(user_course_ids),
        Assignment.is_completed == False,
        Assignment.due_date > now
    ).count() if user_course_ids else 0
    
    completion_rate = (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0.0
    
    return {
        "total_courses": total_courses,
        "total_assignments": total_assignments,
        "completed_assignments": completed_assignments,
        "upcoming_assignments": upcoming_assignments,
        "completion_rate": round(completion_rate, 1),
    }
