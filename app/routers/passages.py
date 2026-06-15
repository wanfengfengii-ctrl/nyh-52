from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.database import get_db
from app import crud, schemas, business_rules
from app.business_rules import BusinessRuleError
from app.text_alignment import compare_two_texts, get_all_diffs_for_passage

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/projects/{project_id}/passages", response_class=HTMLResponse)
async def passages_page(
    request: Request,
    project_id: int,
    version_id: Optional[int] = None,
    volume_no: Optional[int] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    versions = crud.get_versions_by_project(db, project_id)
    
    selected_version = None
    selected_volumes = []
    passages = []
    
    if version_id:
        selected_version = crud.get_version(db, version_id)
        if selected_version:
            selected_volumes = crud.get_volumes_by_version(db, version_id)
            if volume_no:
                passages = crud.get_passages_by_version_volume(db, version_id, volume_no)
            else:
                passages = crud.get_passages_by_version(db, version_id)
    
    error = request.query_params.get("error", None)
    success = request.query_params.get("success", None)
    
    return templates.TemplateResponse("passages.html", {
        "request": request,
        "project": project,
        "versions": versions,
        "selected_version": selected_version,
        "selected_volume": volume_no,
        "selected_volumes": selected_volumes,
        "passages": passages,
        "error": error,
        "success": success
    })


@router.post("/projects/{project_id}/passages")
async def add_passage(
    request: Request,
    project_id: int,
    version_id: int = Form(...),
    volume_no: int = Form(...),
    paragraph_no: int = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    version = crud.get_version(db, version_id)
    if not version or version.project_id != project_id:
        raise HTTPException(status_code=404, detail="版本不存在")
    
    try:
        business_rules.validate_paragraph_continuity(db, version_id, volume_no, paragraph_no)
    except BusinessRuleError as e:
        return RedirectResponse(
            f"/projects/{project_id}/passages?version_id={version_id}&volume_no={volume_no}&error={str(e)}",
            status_code=303
        )
    
    passage_create = schemas.PassageCreate(
        version_id=version_id,
        volume_no=volume_no,
        paragraph_no=paragraph_no,
        content=content
    )
    passage = crud.create_passage(db, passage_create)
    
    refresh_diffs_for_passage(db, project_id, passage.id)
    
    return RedirectResponse(
        f"/projects/{project_id}/passages?version_id={version_id}&volume_no={volume_no}&success=段落添加成功",
        status_code=303
    )


@router.post("/projects/{project_id}/passages/{passage_id}/edit")
async def edit_passage(
    request: Request,
    project_id: int,
    passage_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    passage = crud.get_passage(db, passage_id)
    if not passage:
        raise HTTPException(status_code=404, detail="段落不存在")
    
    old_notes_backup = crud.backup_notes_for_passage(db, passage_id)
    
    passage_update = schemas.PassageUpdate(content=content)
    updated = crud.update_passage(db, passage_id, passage_update)
    
    crud.delete_diffs_by_passage(db, passage_id)
    refresh_diffs_for_passage(db, project_id, passage_id)
    
    crud.restore_notes_to_new_diffs(db, passage_id, old_notes_backup)
    
    return RedirectResponse(
        f"/projects/{project_id}/passages?version_id={passage.version_id}&volume_no={passage.volume_no}&success=段落更新成功，相关校勘结论已标记待复核",
        status_code=303
    )


@router.post("/projects/{project_id}/passages/{passage_id}/delete")
async def delete_passage(
    request: Request,
    project_id: int,
    passage_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    passage = crud.get_passage(db, passage_id)
    if not passage:
        raise HTTPException(status_code=404, detail="段落不存在")
    
    version_id = passage.version_id
    volume_no = passage.volume_no
    
    crud.delete_passage(db, passage_id)
    
    return RedirectResponse(
        f"/projects/{project_id}/passages?version_id={version_id}&volume_no={volume_no}&success=段落已删除",
        status_code=303
    )


def refresh_diffs_for_passage(db: Session, project_id: int, passage_id: int):
    passage = crud.get_passage(db, passage_id)
    if not passage:
        return
    
    versions = crud.get_versions_by_project(db, project_id)
    if len(versions) < 2:
        return
    
    passages_by_location = {}
    version_ids_by_name = {}
    
    for v in versions:
        version_ids_by_name[v.name] = v.id
        p = crud.get_passage_by_location(db, v.id, passage.volume_no, passage.paragraph_no)
        if p:
            passages_by_location[v.name] = p.content
    
    if len(passages_by_location) < 2:
        return
    
    all_diffs = get_all_diffs_for_passage(
        passages_by_location,
        passage_id,
        project_id,
        version_ids_by_name
    )
    
    for diff_data in all_diffs:
        desc = diff_data.pop("description", None)
        base_version_name = diff_data.pop("base_version_name", None)
        version_name = diff_data.pop("version_name", None)
        
        diff_create = schemas.DiffCreate(**diff_data)
        crud.create_diff(db, diff_create)
