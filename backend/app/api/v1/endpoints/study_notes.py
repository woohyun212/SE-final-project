from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.study_note import StudyNoteCreate, StudyNoteUpdate, StudyNoteResponse
from app.services.study_note_service import StudyNoteService
from app.services.course_service import CourseService

router = APIRouter(tags=["학습노트"])

@router.get("/courses/{course_id}/notes", response_model=List[StudyNoteResponse])
def list_notes(course_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = StudyNoteService(db)
    return service.get_notes(course_id)

@router.post("/courses/{course_id}/notes", response_model=StudyNoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(course_id: int, data: StudyNoteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = StudyNoteService(db)
    return service.create_note(course_id, data)

@router.get("/courses/{course_id}/notes/{note_id}", response_model=StudyNoteResponse)
def get_note(course_id: int, note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = StudyNoteService(db)
    note = service.get_note(course_id, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="노트를 찾을 수 없습니다.")
    return note

@router.put("/courses/{course_id}/notes/{note_id}", response_model=StudyNoteResponse)
def update_note(course_id: int, note_id: int, data: StudyNoteUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = StudyNoteService(db)
    note = service.update_note(course_id, note_id, data)
    if not note:
        raise HTTPException(status_code=404, detail="노트를 찾을 수 없습니다.")
    return note

@router.delete("/courses/{course_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(course_id: int, note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course_service = CourseService(db)
    if not course_service.get_course(current_user.id, course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다.")
    service = StudyNoteService(db)
    if not service.delete_note(course_id, note_id):
        raise HTTPException(status_code=404, detail="노트를 찾을 수 없습니다.")
