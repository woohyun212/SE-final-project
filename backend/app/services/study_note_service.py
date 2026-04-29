from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.study_note import StudyNote
from app.schemas.study_note import StudyNoteCreate, StudyNoteUpdate

class StudyNoteService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_notes(self, course_id: int) -> List[StudyNote]:
        return self.db.query(StudyNote).filter(StudyNote.course_id == course_id).all()
    
    def get_note(self, course_id: int, note_id: int) -> Optional[StudyNote]:
        return self.db.query(StudyNote).filter(
            StudyNote.course_id == course_id,
            StudyNote.id == note_id
        ).first()
    
    def create_note(self, course_id: int, data: StudyNoteCreate) -> StudyNote:
        note = StudyNote(course_id=course_id, **data.model_dump())
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note
    
    def update_note(self, course_id: int, note_id: int, data: StudyNoteUpdate) -> Optional[StudyNote]:
        note = self.get_note(course_id, note_id)
        if not note:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(note, key, value)
        note.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(note)
        return note
    
    def delete_note(self, course_id: int, note_id: int) -> bool:
        note = self.get_note(course_id, note_id)
        if not note:
            return False
        self.db.delete(note)
        self.db.commit()
        return True
