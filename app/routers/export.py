from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import quote

from app.database import get_db
from app import crud, export

router = APIRouter()


@router.get("/projects/{project_id}/dashboard")
async def dashboard(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    from fastapi.templating import Jinja2Templates
    import os
    
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    stats = crud.get_project_stats(db, project_id)
    diff_summary = __import__("app.business_rules", fromlist=["business_rules"]).get_diff_status_summary(db, project_id)
    
    versions = crud.get_versions_by_project(db, project_id)
    versions_data = []
    for v in versions:
        volumes = crud.get_volumes_by_version(db, v.id)
        volumes_data = []
        for vol in volumes:
            passages = crud.get_passages_by_version_volume(db, v.id, vol)
            total_diffs = 0
            finalized_diffs = 0
            for p in passages:
                diffs = crud.get_diffs_by_passage(db, p.id)
                total_diffs += len(diffs)
                finalized_diffs += sum(1 for d in diffs if d.status == "finalized")
            
            can_complete = True
            if total_diffs > 0:
                can_complete = finalized_diffs == total_diffs
            
            volumes_data.append({
                "volume": vol,
                "passage_count": len(passages),
                "total_diffs": total_diffs,
                "finalized_diffs": finalized_diffs,
                "progress": round((finalized_diffs / total_diffs * 100), 1) if total_diffs > 0 else 100,
                "can_complete": can_complete
            })
        
        versions_data.append({
            "version": v,
            "volumes": volumes_data
        })
    
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
    templates = Jinja2Templates(directory=templates_dir)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "project": project,
        "stats": stats,
        "diff_summary": diff_summary,
        "versions_data": versions_data
    })


@router.get("/projects/{project_id}/export")
async def export_project(
    project_id: int,
    volume_no: Optional[int] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    content = export.generate_export_text(db, project_id, volume_no)
    
    filename = f"collation_report_project_{project_id}"
    if volume_no:
        filename = f"collation_report_project_{project_id}_vol_{volume_no}"
    filename += ".txt"
    
    encoded_filename = quote(f"{project.name}_校勘报告.txt")
    if volume_no:
        encoded_filename = quote(f"{project.name}_卷{volume_no}_校勘报告.txt")
    
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}; filename*=UTF-8''{encoded_filename}"}
    )


@router.get("/projects/{project_id}/export/recommended")
async def export_recommended(
    project_id: int,
    volume_no: Optional[int] = None,
    include_evidence: bool = True,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    content = export.generate_recommended_text_export(db, project_id, volume_no, include_evidence)
    
    filename = f"recommended_text_project_{project_id}"
    if volume_no:
        filename = f"recommended_text_project_{project_id}_vol_{volume_no}"
    filename += ".txt"
    
    encoded_filename = quote(f"{project.name}_推荐文本整理本.txt")
    if volume_no:
        encoded_filename = quote(f"{project.name}_卷{volume_no}_推荐文本.txt")
    
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}; filename*=UTF-8''{encoded_filename}"}
    )


@router.get("/projects/{project_id}/export/collaboration")
async def export_collaboration(
    project_id: int,
    volume_no: Optional[int] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    content = export.generate_collaboration_report(db, project_id, volume_no)
    
    filename = f"collaboration_report_project_{project_id}"
    if volume_no:
        filename = f"collaboration_report_project_{project_id}_vol_{volume_no}"
    filename += ".txt"
    
    encoded_filename = quote(f"{project.name}_协同校勘报告.txt")
    if volume_no:
        encoded_filename = quote(f"{project.name}_卷{volume_no}_协同报告.txt")
    
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}; filename*=UTF-8''{encoded_filename}"}
    )
