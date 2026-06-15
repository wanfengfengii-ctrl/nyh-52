from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
import os
from urllib.parse import quote
from datetime import datetime

from app.database import get_db
from app import crud, schemas, controversy_analysis

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/projects/{project_id}/controversy", response_class=HTMLResponse)
async def controversy_analysis_page(
    request: Request,
    project_id: int,
    time_period_start: Optional[str] = None,
    time_period_end: Optional[str] = None,
    region_filter: Optional[str] = None,
    diff_type_filter: Optional[str] = None,
    version_system_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    versions = crud.get_versions_with_metadata(db, project_id)
    diffs = crud.get_diffs_by_project(db, project_id)
    reports = crud.get_controversy_reports_by_project(db, project_id)

    analysis_result = None
    if diffs:
        try:
            analysis_result = controversy_analysis.analyze_controversy_heat(
                db, project_id,
                time_period_start, time_period_end,
                region_filter, diff_type_filter, version_system_filter
            )
        except Exception as e:
            analysis_result = None

    regions = sorted(set([v.region or "未知地域" for v in versions]))
    version_systems = sorted(set([v.version_system or "未知系统" for v in versions]))
    diff_types = sorted(set([d.diff_type for d in diffs]))
    periods = [p["label"] for p in controversy_analysis.HISTORICAL_PERIODS]

    return templates.TemplateResponse("controversy_analysis.html", {
        "request": request,
        "project": project,
        "versions": versions,
        "diffs": diffs,
        "reports": reports,
        "analysis_result": analysis_result,
        "regions": regions,
        "version_systems": version_systems,
        "diff_types": diff_types,
        "periods": periods,
        "time_period_start": time_period_start,
        "time_period_end": time_period_end,
        "region_filter": region_filter,
        "diff_type_filter": diff_type_filter,
        "version_system_filter": version_system_filter,
        "get_heat_level_label": controversy_analysis.get_heat_level_label,
        "get_evolution_type_label": controversy_analysis.get_evolution_type_label
    })


@router.get("/api/projects/{project_id}/controversy/analyze")
async def analyze_controversy_api(
    project_id: int,
    time_period_start: Optional[str] = None,
    time_period_end: Optional[str] = None,
    region_filter: Optional[str] = None,
    diff_type_filter: Optional[str] = None,
    version_system_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = controversy_analysis.analyze_controversy_heat(
        db, project_id,
        time_period_start, time_period_end,
        region_filter, diff_type_filter, version_system_filter
    )

    return result


@router.get("/api/projects/{project_id}/controversy/diff/{diff_id}")
async def get_diff_controversy_detail_api(
    project_id: int,
    diff_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    try:
        result = controversy_analysis.get_diff_controversy_detail(db, diff_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/projects/{project_id}/controversy/timeline")
async def get_controversy_timeline_api(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    timeline = controversy_analysis.generate_controversy_timeline(db, project_id)
    return {
        "project_id": project_id,
        "timeline": timeline
    }


@router.get("/api/projects/{project_id}/controversy/diff/{diff_id}/evolution")
async def get_diff_evolution_path_api(
    project_id: int,
    diff_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    diff = crud.get_diff(db, diff_id)
    if not diff:
        raise HTTPException(status_code=404, detail="异文不存在")

    evolution_path = controversy_analysis.get_diff_evolution_path(db, diff)
    evolution_type = controversy_analysis.classify_diff_evolution_type(db, diff)

    return {
        "diff_id": diff_id,
        "evolution_type": evolution_type,
        "evolution_type_label": controversy_analysis.get_evolution_type_label(evolution_type),
        "evolution_path": evolution_path
    }


@router.get("/api/projects/{project_id}/controversy/heat-ranking")
async def get_controversy_heat_ranking_api(
    project_id: int,
    top_n: int = 20,
    diff_type_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    diffs = crud.get_diffs_by_project(db, project_id)
    heat_items = []

    for diff in diffs:
        if diff_type_filter and diff.diff_type != diff_type_filter:
            continue
        controversy_data = controversy_analysis.analyze_diff_controversy(db, diff)
        heat_items.append(schemas.ControversyHeatItem(**controversy_data))

    heat_items.sort(key=lambda x: x.controversy_score, reverse=True)
    top_items = heat_items[:top_n]

    return {
        "project_id": project_id,
        "total_analyzed": len(heat_items),
        "top_n": top_n,
        "ranking": top_items
    }


@router.get("/api/projects/{project_id}/controversy/regional-distribution")
async def get_regional_distribution_api(
    project_id: int,
    diff_type_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    distribution = controversy_analysis.analyze_regional_distribution(db, project_id, diff_type_filter)

    return {
        "project_id": project_id,
        "diff_type_filter": diff_type_filter,
        "distribution": distribution
    }


@router.get("/api/projects/{project_id}/controversy/temporal-evolution")
async def get_temporal_evolution_api(
    project_id: int,
    diff_type_filter: Optional[str] = None,
    region_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    evolution = controversy_analysis.analyze_temporal_evolution(db, project_id, diff_type_filter, region_filter)

    return {
        "project_id": project_id,
        "diff_type_filter": diff_type_filter,
        "region_filter": region_filter,
        "evolution": evolution
    }


@router.get("/api/projects/{project_id}/controversy/version-system-distribution")
async def get_version_system_distribution_api(
    project_id: int,
    diff_type_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    distribution = controversy_analysis.analyze_version_system_distribution(db, project_id, diff_type_filter)

    return {
        "project_id": project_id,
        "diff_type_filter": diff_type_filter,
        "distribution": distribution
    }


@router.post("/api/projects/{project_id}/controversy/reports")
async def create_controversy_report_api(
    project_id: int,
    time_period_start: Optional[str] = Form(None),
    time_period_end: Optional[str] = Form(None),
    region_filter: Optional[str] = Form(None),
    diff_type_filter: Optional[str] = Form(None),
    version_system_filter: Optional[str] = Form(None),
    created_by: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    analysis_result = controversy_analysis.analyze_controversy_heat(
        db, project_id,
        time_period_start, time_period_end,
        region_filter, diff_type_filter, version_system_filter
    )

    content, summary, stats = controversy_analysis.generate_controversy_report_content(
        db, project_id, analysis_result, created_by
    )

    title = f"异文争议分析报告"
    if analysis_result.diff_type_filter:
        title = f"{analysis_result.diff_type_filter}类{title}"
    if analysis_result.region_filter:
        title = f"{analysis_result.region_filter}{title}"

    report_data = schemas.ControversyReportCreate(
        project_id=project_id,
        title=title,
        report_type="controversy_analysis",
        time_period_start=time_period_start,
        time_period_end=time_period_end,
        region_filter=region_filter,
        diff_type_filter=diff_type_filter,
        content=content,
        summary=summary,
        analysis_method=analysis_result.analysis_method,
        findings_count=len(analysis_result.key_findings),
        high_controversy_count=stats["high_controversy_count"],
        stable_inheritance_count=stats["stable_inheritance_count"],
        late_addition_count=stats["late_addition_count"],
        unresolved_count=stats["unresolved_count"],
        created_by=created_by
    )

    report = crud.create_controversy_report(db, report_data)

    return {
        "status": "success",
        "message": "报告生成成功",
        "report_id": report.id,
        "report": report
    }


@router.get("/api/projects/{project_id}/controversy/reports")
async def list_controversy_reports_api(
    project_id: int,
    report_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    reports = crud.get_controversy_reports_by_project(db, project_id, report_type)

    return {
        "project_id": project_id,
        "report_type": report_type,
        "count": len(reports),
        "reports": reports
    }


@router.get("/api/projects/{project_id}/controversy/reports/{report_id}")
async def get_controversy_report_api(
    project_id: int,
    report_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    report = crud.get_controversy_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return report


@router.delete("/api/projects/{project_id}/controversy/reports/{report_id}")
async def delete_controversy_report_api(
    project_id: int,
    report_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    report = crud.delete_controversy_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return {"status": "success", "message": "报告已删除"}


@router.get("/projects/{project_id}/controversy/reports/{report_id}", response_class=HTMLResponse)
async def view_controversy_report_page(
    request: Request,
    project_id: int,
    report_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    report = crud.get_controversy_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return templates.TemplateResponse("controversy_report.html", {
        "request": request,
        "project": project,
        "report": report
    })


@router.get("/projects/{project_id}/controversy/reports/{report_id}/export")
async def export_controversy_report(
    project_id: int,
    report_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    report = crud.get_controversy_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    filename = f"controversy_report_project_{project_id}_{report_id}.txt"
    encoded_filename = quote(f"{project.name}_异文争议分析报告_{report_id}.txt")

    return PlainTextResponse(
        content=report.content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}; filename*=UTF-8''{encoded_filename}"}
    )


@router.put("/api/versions/{version_id}/metadata")
async def update_version_metadata_api(
    version_id: int,
    version_update: schemas.VersionUpdate,
    db: Session = Depends(get_db)
):
    version = crud.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    updated = crud.update_version(db, version_id, version_update)
    return {
        "status": "success",
        "message": "版本元数据更新成功",
        "version": updated
    }


@router.get("/api/projects/{project_id}/controversy/statistics")
async def get_controversy_statistics_api(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    diffs = crud.get_diffs_by_project(db, project_id)
    total_diffs = len(diffs)

    stable_count = 0
    late_count = 0
    unresolved_count = 0
    divergent_count = 0
    gradual_count = 0
    insufficient_count = 0

    for diff in diffs:
        evo_type = controversy_analysis.classify_diff_evolution_type(db, diff)
        if evo_type == "stable_inheritance":
            stable_count += 1
        elif evo_type == "late_addition":
            late_count += 1
        elif evo_type == "unresolved_controversy":
            unresolved_count += 1
        elif evo_type == "divergent_evolution":
            divergent_count += 1
        elif evo_type == "gradual_evolution":
            gradual_count += 1
        else:
            insufficient_count += 1

    return {
        "project_id": project_id,
        "total_diffs": total_diffs,
        "evolution_types": {
            "stable_inheritance": {
                "count": stable_count,
                "label": "长期稳定传承",
                "percentage": round(stable_count / total_diffs * 100, 1) if total_diffs > 0 else 0
            },
            "late_addition": {
                "count": late_count,
                "label": "后期增改",
                "percentage": round(late_count / total_diffs * 100, 1) if total_diffs > 0 else 0
            },
            "unresolved_controversy": {
                "count": unresolved_count,
                "label": "争议未决",
                "percentage": round(unresolved_count / total_diffs * 100, 1) if total_diffs > 0 else 0
            },
            "divergent_evolution": {
                "count": divergent_count,
                "label": "分化演变",
                "percentage": round(divergent_count / total_diffs * 100, 1) if total_diffs > 0 else 0
            },
            "gradual_evolution": {
                "count": gradual_count,
                "label": "渐进演变",
                "percentage": round(gradual_count / total_diffs * 100, 1) if total_diffs > 0 else 0
            },
            "insufficient_data": {
                "count": insufficient_count,
                "label": "数据不足",
                "percentage": round(insufficient_count / total_diffs * 100, 1) if total_diffs > 0 else 0
            }
        }
    }
