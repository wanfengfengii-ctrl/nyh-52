from sqlalchemy.orm import Session
from app import crud, schemas
from typing import Optional, Tuple


class BusinessRuleError(Exception):
    pass


def validate_version_name_unique(db: Session, project_id: int, name: str, 
                                 exclude_version_id: Optional[int] = None) -> None:
    existing = crud.get_version_by_name(db, project_id, name)
    if existing:
        if exclude_version_id is None or existing.id != exclude_version_id:
            raise BusinessRuleError(f"版本名称 '{name}' 在该项目中已存在，同一项目下版本名称不能重复")


def validate_paragraph_continuity(db: Session, version_id: int, volume_no: int, 
                                   paragraph_no: int) -> None:
    existing_numbers = crud.get_passage_paragraph_numbers(db, version_id, volume_no)
    
    if paragraph_no in existing_numbers:
        raise BusinessRuleError(f"段落编号 {paragraph_no} 在该卷中已存在，不能重复")
    
    if existing_numbers:
        max_num = max(existing_numbers)
        min_num = min(existing_numbers)
        
        if paragraph_no > max_num + 1:
            raise BusinessRuleError(
                f"段落编号必须连续：当前最大编号为 {max_num}，下一个编号应为 {max_num + 1}"
            )
        elif paragraph_no < min_num - 1:
            raise BusinessRuleError(
                f"段落编号必须连续：当前最小编号为 {min_num}，不能插入编号 {paragraph_no}"
            )
        elif min_num < paragraph_no <= max_num and paragraph_no not in existing_numbers:
            pass


def validate_final_note_has_evidence(note: schemas.CollationNoteBase) -> None:
    if note.is_final and (not note.evidence or not note.evidence.strip()):
        raise BusinessRuleError("未提供文献依据的校勘意见不能标记为定论")


def validate_volume_can_be_completed(db: Session, project_id: int, version_id: int, 
                                      volume_no: int) -> Tuple[bool, str]:
    passages = crud.get_passages_by_version_volume(db, version_id, volume_no)
    
    if not passages:
        return False, "该卷没有录入段落"
    
    all_diffs = []
    for passage in passages:
        diffs = crud.get_diffs_by_passage(db, passage.id)
        all_diffs.extend(diffs)
    
    pending_count = sum(1 for d in all_diffs if d.status != "finalized")
    
    if pending_count > 0:
        return False, f"该卷存在 {pending_count} 个未处理差异，不能完成整卷校勘"
    
    return True, "可以完成整卷校勘"


def check_passage_modification_needs_review(db: Session, passage_id: int) -> None:
    crud.mark_notes_for_review_by_passage(db, passage_id)


def get_diff_status_summary(db: Session, project_id: int) -> dict:
    diffs = crud.get_diffs_by_project(db, project_id)
    summary = {
        "total": len(diffs),
        "pending": 0,
        "reviewed": 0,
        "finalized": 0,
        "by_type": {
            "missing": 0,
            "variant": 0,
            "added": 0,
            "reversed": 0
        }
    }
    
    for d in diffs:
        summary[d.status] = summary.get(d.status, 0) + 1
        if d.diff_type in summary["by_type"]:
            summary["by_type"][d.diff_type] += 1
    
    return summary
