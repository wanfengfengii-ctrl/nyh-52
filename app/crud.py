from sqlalchemy.orm import Session
from app import models, schemas
from typing import List, Optional


def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).order_by(models.Project.created_at.desc()).offset(skip).limit(limit).all()


def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_versions_by_project(db: Session, project_id: int):
    return db.query(models.Version).filter(models.Version.project_id == project_id).all()


def get_version(db: Session, version_id: int):
    return db.query(models.Version).filter(models.Version.id == version_id).first()


def get_version_by_name(db: Session, project_id: int, name: str):
    return db.query(models.Version).filter(
        models.Version.project_id == project_id,
        models.Version.name == name
    ).first()


def create_version(db: Session, version: schemas.VersionCreate):
    db_version = models.Version(**version.model_dump())
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version


def get_passages_by_version(db: Session, version_id: int):
    return db.query(models.Passage).filter(
        models.Passage.version_id == version_id
    ).order_by(models.Passage.volume_no, models.Passage.paragraph_no).all()


def get_passages_by_version_volume(db: Session, version_id: int, volume_no: int):
    return db.query(models.Passage).filter(
        models.Passage.version_id == version_id,
        models.Passage.volume_no == volume_no
    ).order_by(models.Passage.paragraph_no).all()


def get_passage(db: Session, passage_id: int):
    return db.query(models.Passage).filter(models.Passage.id == passage_id).first()


def get_passage_by_location(db: Session, version_id: int, volume_no: int, paragraph_no: int):
    return db.query(models.Passage).filter(
        models.Passage.version_id == version_id,
        models.Passage.volume_no == volume_no,
        models.Passage.paragraph_no == paragraph_no
    ).first()


def get_passage_paragraph_numbers(db: Session, version_id: int, volume_no: int):
    passages = db.query(models.Passage).filter(
        models.Passage.version_id == version_id,
        models.Passage.volume_no == volume_no
    ).order_by(models.Passage.paragraph_no).all()
    return [p.paragraph_no for p in passages]


def create_passage(db: Session, passage: schemas.PassageCreate):
    db_passage = models.Passage(**passage.model_dump())
    db.add(db_passage)
    db.commit()
    db.refresh(db_passage)
    return db_passage


def update_passage(db: Session, passage_id: int, passage_update: schemas.PassageUpdate):
    db_passage = db.query(models.Passage).filter(models.Passage.id == passage_id).first()
    if db_passage:
        for key, value in passage_update.model_dump().items():
            setattr(db_passage, key, value)
        db.commit()
        db.refresh(db_passage)
    return db_passage


def delete_passage(db: Session, passage_id: int):
    db_passage = db.query(models.Passage).filter(models.Passage.id == passage_id).first()
    if db_passage:
        db.delete(db_passage)
        db.commit()
    return db_passage


def get_volumes_by_version(db: Session, version_id: int):
    passages = db.query(models.Passage).filter(
        models.Passage.version_id == version_id
    ).all()
    volumes = sorted(set(p.volume_no for p in passages))
    return volumes


def get_diffs_by_project(db: Session, project_id: int):
    return db.query(models.Diff).filter(models.Diff.project_id == project_id).all()


def get_diffs_by_passage(db: Session, passage_id: int):
    return db.query(models.Diff).filter(models.Diff.passage_id == passage_id).all()


def get_diff(db: Session, diff_id: int):
    return db.query(models.Diff).filter(models.Diff.id == diff_id).first()


def create_diff(db: Session, diff: schemas.DiffCreate):
    db_diff = models.Diff(**diff.model_dump())
    db.add(db_diff)
    db.commit()
    db.refresh(db_diff)
    return db_diff


def update_diff_status(db: Session, diff_id: int, status: str):
    db_diff = db.query(models.Diff).filter(models.Diff.id == diff_id).first()
    if db_diff:
        db_diff.status = status
        db.commit()
        db.refresh(db_diff)
    return db_diff


def delete_diffs_by_passage(db: Session, passage_id: int):
    db.query(models.Diff).filter(models.Diff.passage_id == passage_id).delete()
    db.commit()


def get_collation_notes_by_diff(db: Session, diff_id: int):
    return db.query(models.CollationNote).filter(
        models.CollationNote.diff_id == diff_id
    ).order_by(models.CollationNote.created_at.desc()).all()


def get_collation_note(db: Session, note_id: int):
    return db.query(models.CollationNote).filter(models.CollationNote.id == note_id).first()


def create_collation_note(db: Session, note: schemas.CollationNoteCreate):
    db_note = models.CollationNote(**note.model_dump())
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


def update_collation_note_final(db: Session, note_id: int, is_final: bool):
    db_note = db.query(models.CollationNote).filter(models.CollationNote.id == note_id).first()
    if db_note:
        db_note.is_final = is_final
        if is_final:
            db_note.needs_review = False
        db.commit()
        db.refresh(db_note)
    return db_note


def mark_notes_for_review_by_passage(db: Session, passage_id: int):
    diffs = db.query(models.Diff).filter(models.Diff.passage_id == passage_id).all()
    for diff in diffs:
        notes = db.query(models.CollationNote).filter(
            models.CollationNote.diff_id == diff.id,
            models.CollationNote.is_final == True
        ).all()
        for note in notes:
            note.needs_review = True
            note.is_final = False
    db.commit()


def get_project_stats(db: Session, project_id: int) -> schemas.ProjectStats:
    versions = get_versions_by_project(db, project_id)
    total_versions = len(versions)
    
    total_passages = 0
    for v in versions:
        total_passages += len(get_passages_by_version(db, v.id))
    
    diffs = get_diffs_by_project(db, project_id)
    total_diffs = len(diffs)
    pending_diffs = sum(1 for d in diffs if d.status == "pending")
    reviewed_diffs = sum(1 for d in diffs if d.status == "reviewed")
    finalized_diffs = sum(1 for d in diffs if d.status == "finalized")
    
    progress_percent = 0.0
    if total_diffs > 0:
        progress_percent = round((finalized_diffs / total_diffs) * 100, 1)
    
    return schemas.ProjectStats(
        total_versions=total_versions,
        total_passages=total_passages,
        total_diffs=total_diffs,
        pending_diffs=pending_diffs,
        reviewed_diffs=reviewed_diffs,
        finalized_diffs=finalized_diffs,
        progress_percent=progress_percent
    )
