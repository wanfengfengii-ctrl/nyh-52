from sqlalchemy.orm import Session
from app import crud
from app.text_alignment import DIFF_TYPE_LABELS
from typing import Optional
from datetime import datetime


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


def generate_recommended_text_export(db: Session, project_id: int, 
                                      volume_no: Optional[int] = None,
                                      include_evidence: bool = True) -> str:
    project = crud.get_project(db, project_id)
    if not project:
        return ""
    
    versions = crud.get_versions_by_project(db, project_id)
    if not versions:
        return ""
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"古籍整理本（推荐文本）")
    lines.append(f"项目名称: {project.name}")
    lines.append(f"古籍书名: {project.book_title}")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    
    total_paragraphs = 0
    recommended_count = 0
    reviewed_count = 0
    
    for vol in volumes_to_export:
        lines.append("-" * 60)
        lines.append(f"卷 {vol}")
        lines.append("-" * 60)
        lines.append("")
        
        passages = crud.get_passages_by_version_volume(db, base_version.id, vol)
        
        for passage in passages:
            total_paragraphs += 1
            rt = crud.get_recommended_text(db, project_id, vol, passage.paragraph_no)
            
            lines.append(f"【第 {passage.paragraph_no} 段】")
            
            if rt:
                recommended_count += 1
                if rt.status == "reviewed":
                    reviewed_count += 1
                
                status_mark = ""
                if rt.status == "reviewed":
                    status_mark = " [已审核]"
                elif rt.status == "draft":
                    status_mark = " [草稿]"
                
                lines.append(f"{status_mark}")
                lines.append(f"  {rt.content}")
                lines.append("")
                
                if include_evidence:
                    evidences = crud.get_evidences_by_recommended_text(db, rt.id)
                    if evidences:
                        lines.append("  【校勘依据】")
                        for idx, ev in enumerate(evidences, 1):
                            source_info = f"（来源: {ev.source_version_name}）" if ev.source_version_name else ""
                            lines.append(f"  {idx}. [{ev.evidence_type}]{source_info}")
                            if ev.description:
                                lines.append(f"     {ev.description}")
                        lines.append("")
                
                lines.append(f"  生成人: {rt.generated_by or '系统'}")
                if rt.reviewed_by:
                    lines.append(f"  审核人: {rt.reviewed_by}")
                    if rt.reviewed_at:
                        lines.append(f"  审核时间: {rt.reviewed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                lines.append("")
            else:
                lines.append(f"  [未生成推荐文本]")
                lines.append(f"  （{passage.content}）")
                lines.append("")
            
            lines.append("")
    
    lines.append("=" * 60)
    lines.append("【统计信息】")
    lines.append(f"  总段落数: {total_paragraphs}")
    lines.append(f"  已生成推荐: {recommended_count}")
    lines.append(f"  已审核通过: {reviewed_count}")
    lines.append(f"  完成度: {round((reviewed_count / total_paragraphs * 100), 1) if total_paragraphs > 0 else 0}%")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def generate_collaboration_report(db: Session, project_id: int,
                                   volume_no: Optional[int] = None) -> str:
    project = crud.get_project(db, project_id)
    if not project:
        return ""
    
    versions = crud.get_versions_by_project(db, project_id)
    if not versions:
        return ""
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"协同校勘报告")
    lines.append(f"项目名称: {project.name}")
    lines.append(f"古籍书名: {project.book_title}")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    
    diffs = crud.get_diffs_by_project(db, project_id)
    
    total_proposals = 0
    total_discussions = 0
    accepted_proposals = 0
    
    for diff in diffs:
        proposals = crud.get_proposals_by_diff(db, diff.id)
        discussions = crud.get_discussions_by_diff(db, diff.id)
        
        total_proposals += len(proposals)
        total_discussions += len(discussions)
        accepted_proposals += sum(1 for p in proposals if p.is_accepted)
    
    lines.append("【总体统计】")
    lines.append(f"  差异总数: {len(diffs)}")
    lines.append(f"  校勘方案总数: {total_proposals}")
    lines.append(f"  已采纳方案: {accepted_proposals}")
    lines.append(f"  讨论消息数: {total_discussions}")
    lines.append("")
    
    if total_proposals > 0:
        lines.append("-" * 60)
        lines.append("【校勘方案详情】")
        lines.append("-" * 60)
        lines.append("")
        
        diff_idx = 0
        for diff in diffs:
            proposals = crud.get_proposals_by_diff(db, diff.id)
            if not proposals:
                continue
            
            diff_idx += 1
            version = crud.get_version(db, diff.version_id)
            passage = crud.get_passage(db, diff.passage_id)
            
            lines.append(f"【差异 {diff_idx}】")
            lines.append(f"  类型: {DIFF_TYPE_LABELS.get(diff.diff_type, diff.diff_type)}")
            if version:
                lines.append(f"  版本: {version.name}")
            if passage:
                lines.append(f"  位置: 卷 {passage.volume_no} · 第 {passage.paragraph_no} 段")
            lines.append(f"  状态: {_get_status_label(diff.status)}")
            lines.append("")
            
            for p_idx, p in enumerate(proposals, 1):
                vote_summary = crud.get_vote_summary(db, p.id)
                citations = crud.get_citations_by_proposal(db, p.id)
                review_records = crud.get_review_records_by_proposal(db, p.id)
                
                accepted_mark = " ★已采纳" if p.is_accepted else ""
                lines.append(f"  方案 {p_idx}: {p.title}{accepted_mark}")
                lines.append(f"    提交人: {p.author}")
                lines.append(f"    提交时间: {p.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                lines.append(f"    校勘文本: {p.proposed_text}")
                lines.append(f"    论证理由: {p.rationale}")
                lines.append(f"    投票: 赞成 {vote_summary.agree_count} / 反对 {vote_summary.disagree_count} / 弃权 {vote_summary.abstain_count}")
                lines.append("")
                
                if citations:
                    lines.append(f"    文献引用 ({len(citations)}条):")
                    for c_idx, c in enumerate(citations, 1):
                        lines.append(f"      {c_idx}. {c.title}")
                        if c.author:
                            lines.append(f"         作者: {c.author}")
                        if c.publication:
                            lines.append(f"         出版物: {c.publication}")
                        if c.page_info:
                            lines.append(f"         页码: {c.page_info}")
                        if c.quote_text:
                            lines.append(f"         引文: \"{c.quote_text}\"")
                    lines.append("")
                
                if review_records:
                    lines.append(f"    审核记录 ({len(review_records)}条):")
                    for r_idx, r in enumerate(review_records, 1):
                        result_label = "通过" if r.review_result == "pass" else ("驳回" if r.review_result == "reject" else "评论")
                        lines.append(f"      {r_idx}. [{result_label}] {r.reviewer} - {r.created_at.strftime('%Y-%m-%d %H:%M')}")
                        if r.review_comment:
                            lines.append(f"         意见: {r.review_comment}")
                    lines.append("")
            
            discussions = crud.get_discussions_by_diff(db, diff.id)
            if discussions:
                lines.append(f"    讨论 ({len(discussions)}条):")
                for d_idx, d in enumerate(discussions, 1):
                    lines.append(f"      {d_idx}. {d.author} - {d.created_at.strftime('%Y-%m-%d %H:%M')}")
                    lines.append(f"         {d.content}")
                lines.append("")
    
    return "\n".join(lines)
