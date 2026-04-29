from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate, AssignmentResponse
from app.services.assignment_service import AssignmentService
from app.services.course_service import CourseService

router = APIRouter(tags=["과제"])

@router.get("/courses/{course_id}/assignments", response_model=List[AssignmentResponse])
def list_assignments(course_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = AssignmentService(db)
    return service.get_assignments(course_id)

@router.post("/courses/{course_id}/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(course_id: int, data: AssignmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = AssignmentService(db)
    return service.create_assignment(course_id, data)

@router.get("/courses/{course_id}/assignments/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(course_id: int, assignment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = AssignmentService(db)
    assignment = service.get_assignment(course_id, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="과제를 찾을 수 없습니다.")
    return assignment

@router.put("/courses/{course_id}/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(course_id: int, assignment_id: int, data: AssignmentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = AssignmentService(db)
    assignment = service.update_assignment(course_id, assignment_id, data)
    if not assignment:
        raise HTTPException(status_code=404, detail="과제를 찾을 수 없습니다.")
    return assignment

@router.delete("/courses/{course_id}/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(course_id: int, assignment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = AssignmentService(db)
    if not service.delete_assignment(course_id, assignment_id):
        raise HTTPException(status_code=404, detail="과제를 찾을 수 없습니다.")
