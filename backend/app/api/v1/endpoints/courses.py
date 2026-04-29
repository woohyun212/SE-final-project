from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["강의"])

@router.get("/", response_model=List[CourseResponse])
def list_courses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CourseService(db)
    return service.get_courses(current_user.id)

@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(course_data: CourseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CourseService(db)
    return service.create_course(current_user.id, course_data)

@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CourseService(db)
    course = service.get_course(current_user.id, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    return course

@router.put("/{course_id}", response_model=CourseResponse)
def update_course(course_id: int, course_data: CourseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CourseService(db)
    course = service.update_course(current_user.id, course_id, course_data)
    if not course:
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    return course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CourseService(db)
    if not service.delete_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
