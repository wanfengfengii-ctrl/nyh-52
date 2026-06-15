from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    book_title: str = Field(..., min_length=1, max_length=255)


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VersionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source: Optional[str] = None
    year: Optional[str] = Field(None, max_length=50)


class VersionCreate(VersionBase):
    project_id: int


class Version(VersionBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True


class PassageBase(BaseModel):
    volume_no: int = Field(..., ge=1)
    paragraph_no: int = Field(..., ge=1)
    content: str = Field(..., min_length=1)


class PassageCreate(PassageBase):
    version_id: int


class PassageUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class Passage(PassageBase):
    id: int
    version_id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class DiffBase(BaseModel):
    diff_type: str
    position_start: int
    position_end: int
    text: Optional[str] = None
    reference_text: Optional[str] = None
    status: str = "pending"


class DiffCreate(DiffBase):
    project_id: int
    passage_id: int
    version_id: int


class Diff(DiffBase):
    id: int
    project_id: int
    passage_id: int
    version_id: int

    class Config:
        from_attributes = True


class CollationNoteBase(BaseModel):
    author: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    evidence: Optional[str] = None
    is_final: bool = False
    needs_review: bool = False


class CollationNoteCreate(CollationNoteBase):
    diff_id: int


class CollationNote(CollationNoteBase):
    id: int
    diff_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DiffWithNotes(Diff):
    collation_notes: List[CollationNote] = []


class ProjectStats(BaseModel):
    total_versions: int = 0
    total_passages: int = 0
    total_diffs: int = 0
    pending_diffs: int = 0
    reviewed_diffs: int = 0
    finalized_diffs: int = 0
    progress_percent: float = 0.0
