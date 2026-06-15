from sqlalchemy.orm import Session
from app import crud
from app.text_alignment import DIFF_TYPE_LABELS
from typing import Optional


def generate_export_text(db: Session, project_id: int, 
                         volume_no: Optional[int] = None) -> str:
    project = crud.get_project(db, project_id)
    if not project:
        return ""
    
    versions = crud.get_versions_by_project(db, project_id)
    if not versions:
        return ""
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"古籍校勘报告")
    lines.append(f"项目名称: {project.name}")
    lines.append(f"古籍书名: {project.book_title}")
    lines.append(f"创建时间: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    
    lines.append("【版本信息】")
    for v in versions:
        lines.append(f"  * {v.name}（{v.year or '年代不详'}）- {v.source or '无来源说明'}")
    lines.append("")
    
    base_version = versions[0]
    all_volumes = crud.get_volumes_by_version(db, base_version.id)
    
    if volume_no is not None:
        volumes_to_export = [volume_no] if volume_no in all_volumes else []
    else:
        volumes_to_export = all_volumes
    
    for vol in volumes_to_export:
        lines.append("-" * 60)
        lines.append(f"卷 {vol}")
        lines.append("-" * 60)
        lines.append("")
        
        passages = crud.get_passages_by_version_volume(db, base_version.id, vol)
        
        for passage in passages:
            lines.append(f"【段落 {passage.paragraph_no}】")
            lines.append("")
            
            for version in versions:
                v_passage = crud.get_passage_by_location(db, version.id, vol, passage.paragraph_no)
                if v_passage:
                    lines.append(f"  [{version.name}]")
                    lines.append(f"  {v_passage.content}")
                    lines.append("")
            
            diffs = crud.get_diffs_by_passage(db, passage.id)
            if diffs:
                lines.append("  【校勘差异】")
                for idx, diff in enumerate(diffs, 1):
                    diff_label = DIFF_TYPE_LABELS.get(diff.diff_type, diff.diff_type)
                    lines.append(f"  {idx}. [{diff_label}]")
                    
                    diff_version = next((v for v in versions if v.id == diff.version_id), None)
                    if diff_version:
                        lines.append(f"     版本: {diff_version.name}")
                    
                    if diff.reference_text:
                        lines.append(f"     原文: {diff.reference_text}")
                    if diff.text:
                        lines.append(f"     异文: {diff.text}")
                    lines.append(f"     状态: {_get_status_label(diff.status)}")
                    
                    notes = crud.get_collation_notes_by_diff(db, diff.id)
                    if notes:
                        lines.append(f"     校勘意见:")
                        for n_idx, note in enumerate(notes, 1):
                            final_mark = " ★定论" if note.is_final else ""
                            review_mark = " ⚠待复核" if note.needs_review else ""
                            lines.append(f"       {n_idx}. [{note.author}]{final_mark}{review_mark}")
                            lines.append(f"          意见: {note.content}")
                            if note.evidence:
                                lines.append(f"          依据: {note.evidence}")
                            lines.append(f"          时间: {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    lines.append("")
            lines.append("")
    
    stats = crud.get_project_stats(db, project_id)
    lines.append("=" * 60)
    lines.append("【校勘统计】")
    lines.append(f"  版本总数: {stats.total_versions}")
    lines.append(f"  段落总数: {stats.total_passages}")
    lines.append(f"  差异总数: {stats.total_diffs}")
    lines.append(f"  待处理: {stats.pending_diffs}")
    lines.append(f"  复核中: {stats.reviewed_diffs}")
    lines.append(f"  已定论: {stats.finalized_diffs}")
    lines.append(f"  完成进度: {stats.progress_percent}%")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def _get_status_label(status: str) -> str:
    labels = {
        "pending": "待处理",
        "reviewed": "复核中",
        "finalized": "已定论"
    }
    return labels.get(status, status)
