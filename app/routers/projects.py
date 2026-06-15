from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.database import get_db
from app import crud, schemas, business_rules
from app.business_rules import BusinessRuleError

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    projects = crud.get_projects(db)
    projects_with_stats = []
    for p in projects:
        stats = crud.get_project_stats(db, p.id)
        projects_with_stats.append({"project": p, "stats": stats})
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "projects_with_stats": projects_with_stats
    })


@router.get("/projects/create", response_class=HTMLResponse)
async def create_project_form(request: Request):
    return templates.TemplateResponse("project_create.html", {"request": request})


@router.post("/projects/create")
async def create_project(
    request: Request,
    name: str = Form(...),
    book_title: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project_create = schemas.ProjectCreate(name=name, book_title=book_title, description=description)
    project = crud.create_project(db, project_create)
    return RedirectResponse(f"/projects/{project.id}", status_code=303)


@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    versions = crud.get_versions_by_project(db, project_id)
    stats = crud.get_project_stats(db, project_id)
    diff_summary = business_rules.get_diff_status_summary(db, project_id)
    
    versions_with_volumes = []
    for v in versions:
        volumes = crud.get_volumes_by_version(db, v.id)
        passage_count = len(crud.get_passages_by_version(db, v.id))
        versions_with_volumes.append({
            "version": v,
            "volumes": volumes,
            "passage_count": passage_count
        })
    
    error = request.query_params.get("error", None)
    success = request.query_params.get("success", None)
    
    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project": project,
        "versions_with_volumes": versions_with_volumes,
        "stats": stats,
        "diff_summary": diff_summary,
        "error": error,
        "success": success
    })


@router.post("/projects/{project_id}/versions")
async def add_version(
    request: Request,
    project_id: int,
    name: str = Form(...),
    source: Optional[str] = Form(None),
    year: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    try:
        business_rules.validate_version_name_unique(db, project_id, name)
    except BusinessRuleError as e:
        return RedirectResponse(f"/projects/{project_id}?error={str(e)}", status_code=303)
    
    version_create = schemas.VersionCreate(
        project_id=project_id,
        name=name,
        source=source,
        year=year
    )
    crud.create_version(db, version_create)
    return RedirectResponse(f"/projects/{project_id}?success=版本添加成功", status_code=303)
