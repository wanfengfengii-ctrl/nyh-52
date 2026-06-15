from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.database import get_db
from app import crud, schemas, business_rules
from app.text_alignment import (
    align_texts, render_segment_html, DIFF_TYPE_LABELS, DIFF_TYPE_COLORS
)

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/projects/{project_id}/compare", response_class=HTMLResponse)
async def compare_page(
    request: Request,
    project_id: int,
    volume_no: Optional[int] = None,
    paragraph_no: Optional[int] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    versions = crud.get_versions_by_project(db, project_id)
    
    if len(versions) < 2:
        return templates.TemplateResponse("version_compare.html", {
            "request": request,
            "project": project,
            "versions": versions,
            "error": "请至少添加2个版本后再进行比对",
            "volumes": [],
            "selected_volume": volume_no,
            "selected_paragraph": paragraph_no,
            "alignment_result": None,
            "diff_type_labels": DIFF_TYPE_LABELS,
            "diff_type_colors": DIFF_TYPE_COLORS,
            "all_diffs": [],
            "pending_count": 0
        })
    
    all_volumes = set()
    for v in versions:
        vols = crud.get_volumes_by_version(db, v.id)
        all_volumes.update(vols)
    volumes = sorted(all_volumes)
    
    alignment_result = None
    all_diffs = []
    pending_count = 0
    
    if volume_no is not None and paragraph_no is not None:
        passages_dict = {}
        version_ids_by_name = {}
        
        for v in versions:
            version_ids_by_name[v.name] = v.id
            p = crud.get_passage_by_location(db, v.id, volume_no, paragraph_no)
            if p:
                passages_dict[v.name] = p.content
        
        if passages_dict:
            alignment_result = align_texts(passages_dict)
            
            rendered_result = {}
            for v_name, segments in alignment_result.items():
                html_segments = []
                for seg in segments:
                    html_segments.append({
                        "type": seg["type"],
                        "text": seg["text"],
                        "html": render_segment_html(seg),
                        "diffs": seg["diffs"]
                    })
                rendered_result[v_name] = html_segments
            alignment_result = rendered_result
            
            base_version = versions[0]
            base_passage = crud.get_passage_by_location(db, base_version.id, volume_no, paragraph_no)
            if base_passage:
                all_diffs = crud.get_diffs_by_passage(db, base_passage.id)
                pending_count = sum(1 for d in all_diffs if d.status == "pending")
    
    stats = crud.get_project_stats(db, project_id)
    
    return templates.TemplateResponse("version_compare.html", {
        "request": request,
        "project": project,
        "versions": versions,
        "volumes": volumes,
        "selected_volume": volume_no,
        "selected_paragraph": paragraph_no,
        "alignment_result": alignment_result,
        "diff_type_labels": DIFF_TYPE_LABELS,
        "diff_type_colors": DIFF_TYPE_COLORS,
        "all_diffs": all_diffs,
        "pending_count": pending_count,
        "stats": stats,
        "error": None
    })


@router.get("/projects/{project_id}/collation/{diff_id}", response_class=HTMLResponse)
async def collation_page(
    request: Request,
    project_id: int,
    diff_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    diff = crud.get_diff(db, diff_id)
    if not diff:
        raise HTTPException(status_code=404, detail="差异不存在")
    
    notes = crud.get_collation_notes_by_diff(db, diff_id)
    
    version = crud.get_version(db, diff.version_id)
    passage = crud.get_passage(db, diff.passage_id)
    
    diff_label = DIFF_TYPE_LABELS.get(diff.diff_type, diff.diff_type)
    diff_color = DIFF_TYPE_COLORS.get(diff.diff_type, "#333")
    
    error = request.query_params.get("error", None)
    success = request.query_params.get("success", None)
    
    return templates.TemplateResponse("collation_view.html", {
        "request": request,
        "project": project,
        "diff": diff,
        "notes": notes,
        "version": version,
        "passage": passage,
        "diff_label": diff_label,
        "diff_color": diff_color,
        "error": error,
        "success": success
    })


@router.post("/projects/{project_id}/collation/{diff_id}/notes")
async def add_collation_note(
    request: Request,
    project_id: int,
    diff_id: int,
    author: str = Form(...),
    content: str = Form(...),
    evidence: Optional[str] = Form(None),
    is_final: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    diff = crud.get_diff(db, diff_id)
    if not diff:
        raise HTTPException(status_code=404, detail="差异不存在")
    
    is_final_bool = is_final is not None
    
    note_data = schemas.CollationNoteBase(
        author=author,
        content=content,
        evidence=evidence,
        is_final=is_final_bool,
        needs_review=False
    )
    
    try:
        business_rules.validate_final_note_has_evidence(note_data)
    except business_rules.BusinessRuleError as e:
        return RedirectResponse(
            f"/projects/{project_id}/collation/{diff_id}?error={str(e)}",
            status_code=303
        )
    
    note_create = schemas.CollationNoteCreate(diff_id=diff_id, **note_data.model_dump())
    crud.create_collation_note(db, note_create)
    
    if is_final_bool:
        crud.update_diff_status(db, diff_id, "finalized")
    else:
        crud.update_diff_status(db, diff_id, "reviewed")
    
    return RedirectResponse(
        f"/projects/{project_id}/collation/{diff_id}?success=校勘意见已提交",
        status_code=303
    )


@router.post("/projects/{project_id}/collation/{diff_id}/notes/{note_id}/final")
async def mark_note_final(
    request: Request,
    project_id: int,
    diff_id: int,
    note_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    note = crud.get_collation_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="校勘意见不存在")
    
    if not note.evidence or not note.evidence.strip():
        return RedirectResponse(
            f"/projects/{project_id}/collation/{diff_id}?error=未提供文献依据的校勘意见不能标记为定论",
            status_code=303
        )
    
    crud.update_collation_note_final(db, note_id, True)
    crud.update_diff_status(db, diff_id, "finalized")
    
    return RedirectResponse(
        f"/projects/{project_id}/collation/{diff_id}?success=已标记为定论",
        status_code=303
    )


@router.post("/projects/{project_id}/collation/{diff_id}/notes/{note_id}/review")
async def mark_note_needs_review(
    request: Request,
    project_id: int,
    diff_id: int,
    note_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    note = crud.get_collation_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="校勘意见不存在")
    
    db_note = crud.get_collation_note(db, note_id)
    if db_note:
        db_note.needs_review = True
        db_note.is_final = False
        db.commit()
    
    crud.update_diff_status(db, diff_id, "reviewed")
    
    return RedirectResponse(
        f"/projects/{project_id}/collation/{diff_id}?success=已发起复核",
        status_code=303
    )
