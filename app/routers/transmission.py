from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import os
import json
from datetime import datetime
from collections import deque

from app.database import get_db
from app import crud, schemas, models

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


def analyze_transmission_paths(
    db: Session,
    project_id: int,
    target_diff_id: int,
    max_depth: int = 5
) -> schemas.TransmissionAnalysisResult:
    target_diff = crud.get_diff(db, target_diff_id)
    if not target_diff:
        raise HTTPException(status_code=404, detail="目标异文不存在")

    versions = crud.get_versions_by_project(db, project_id)
    version_ids = [v.id for v in versions]
    version_names = {v.id: v.name for v in versions}

    lineages = crud.get_version_lineages_by_project(db, project_id)
    adjacency = {v.id: [] for v in versions}
    reverse_adjacency = {v.id: [] for v in versions}
    for lineage in lineages:
        if lineage.parent_version_id in adjacency and lineage.child_version_id in adjacency:
            adjacency[lineage.parent_version_id].append({
                "target": lineage.child_version_id,
                "weight": lineage.confidence,
                "relation_type": lineage.relation_type
            })
            reverse_adjacency[lineage.child_version_id].append({
                "target": lineage.parent_version_id,
                "weight": lineage.confidence,
                "relation_type": lineage.relation_type
            })

    all_diffs = crud.get_diffs_by_project(db, project_id)
    diff_by_version = {}
    for d in all_diffs:
        if d.version_id not in diff_by_version:
            diff_by_version[d.version_id] = []
        diff_by_version[d.version_id].append(d)

    target_text = target_diff.text or ""
    target_type = target_diff.diff_type

    related_versions = []
    for v in versions:
        v_diffs = diff_by_version.get(v.id, [])
        has_similar = False
        for d in v_diffs:
            if d.id == target_diff_id:
                has_similar = True
                break
            if target_text and d.text and target_text == d.text:
                has_similar = True
                break
            if d.diff_type == target_type and d.text and target_text and len(d.text) == len(target_text):
                has_similar = True
                break
        if has_similar:
            related_versions.append(v.id)

    all_paths = []

    def find_paths_bfs(start_id: int, end_id: int, adj: Dict, reverse: bool = False):
        queue = deque([(start_id, [start_id], 0)])
        visited = set()
        paths = []

        while queue:
            current, path, weight = queue.popleft()
            if current == end_id and len(path) > 1:
                paths.append({
                    "path": path if not reverse else list(reversed(path)),
                    "weight": weight,
                    "evidence_count": len(path) - 1
                })
                if len(paths) >= 10:
                    break
                continue

            if len(path) > max_depth:
                continue

            if current in visited and len(path) > 2:
                continue
            visited.add(current)

            for neighbor in adj.get(current, []):
                if neighbor["target"] not in path:
                    new_path = path + [neighbor["target"]]
                    new_weight = weight + neighbor["weight"]
                    queue.append((neighbor["target"], new_path, new_weight))

        return paths

    for start_v in related_versions:
        for end_v in related_versions:
            if start_v != end_v:
                forward_paths = find_paths_bfs(start_v, end_v, adjacency, reverse=False)
                for p in forward_paths:
                    p["direction"] = "forward"
                    all_paths.append(p)

    all_paths.sort(key=lambda x: x["weight"], reverse=True)
    top_paths = all_paths[:20]

    transmission_paths = []
    for p in top_paths:
        path_names = [version_names.get(vid, "未知") for vid in p["path"]]
        path_type = classify_path_type(p, target_type, target_text, diff_by_version)
        transmission_paths.append(schemas.TransmissionPath(
            path=p["path"],
            version_names=path_names,
            total_weight=p["weight"],
            path_type=path_type,
            evidence_count=p["evidence_count"]
        ))

    likely_cause, confidence = determine_likely_cause(
        transmission_paths, target_type, target_text, lineages
    )

    key_findings = generate_key_findings(
        transmission_paths, likely_cause, confidence, target_diff
    )

    return schemas.TransmissionAnalysisResult(
        target_diff_id=target_diff_id,
        analysis_method="multi_feature_path_analysis",
        total_paths=len(transmission_paths),
        transmission_paths=transmission_paths,
        likely_cause=likely_cause,
        confidence=confidence,
        key_findings=key_findings
    )


def classify_path_type(path_info: Dict, diff_type: str, diff_text: str, diff_by_version: Dict) -> str:
    weight = path_info["weight"]
    path_len = len(path_info["path"])

    if weight >= 80 and path_len <= 2:
        return "direct_copy"
    elif weight >= 60:
        if diff_type in ["deletion", "insertion"]:
            return "copy_error"
        else:
            return "version_inheritance"
    elif weight >= 40:
        if diff_text and len(diff_text) <= 2:
            return "copy_error"
        else:
            return "version_inheritance"
    elif path_len > 3:
        return "indirect_transmission"
    else:
        return "unknown"


def determine_likely_cause(
    paths: List[schemas.TransmissionPath],
    diff_type: str,
    diff_text: str,
    lineages: List
) -> tuple:
    if not paths:
        return "unknown", 0

    type_counts = {}
    total_weight = 0
    for p in paths:
        type_counts[p.path_type] = type_counts.get(p.path_type, 0) + 1
        total_weight += p.total_weight

    avg_weight = total_weight / len(paths) if paths else 0

    direct_count = type_counts.get("direct_copy", 0)
    copy_error_count = type_counts.get("copy_error", 0)
    inheritance_count = type_counts.get("version_inheritance", 0)
    indirect_count = type_counts.get("indirect_transmission", 0)

    if direct_count > 0 and avg_weight >= 70:
        cause = "direct_inheritance"
        confidence = min(95, avg_weight + 10)
    elif copy_error_count > inheritance_count and diff_type in ["deletion", "insertion", "substitution"]:
        cause = "copy_error"
        confidence = min(85, 50 + copy_error_count * 10)
    elif inheritance_count > 0:
        cause = "version_inheritance"
        confidence = min(80, avg_weight + 5)
    elif indirect_count > 0:
        cause = "indirect_transmission"
        confidence = min(60, avg_weight)
    else:
        cause = "uncertain"
        confidence = 30

    if diff_text and len(diff_text) == 1 and diff_type == "substitution":
        if confidence < 70:
            cause = "copy_error"
            confidence = max(confidence, 55)

    return cause, int(confidence)


def generate_key_findings(
    paths: List[schemas.TransmissionPath],
    likely_cause: str,
    confidence: int,
    target_diff
) -> List[str]:
    findings = []

    if not paths:
        findings.append("未找到明显的传播路径，该异文可能是独立产生的")
        return findings

    findings.append(f"共发现 {len(paths)} 条可能的传播路径")

    if likely_cause == "direct_inheritance":
        findings.append("该异文很可能是通过直接承袭的方式在版本间传播")
    elif likely_cause == "copy_error":
        findings.append("该异文具有传抄讹误的特征，可能是在抄写过程中产生")
    elif likely_cause == "version_inheritance":
        findings.append("该异文表现出版本承袭的特征，存在系统性传承关系")
    elif likely_cause == "indirect_transmission":
        findings.append("该异文可能通过间接途径传播，涉及多个中间版本")
    else:
        findings.append("该异文的传播原因尚不确定，需要进一步研究")

    findings.append(f"综合置信度为 {confidence}%")

    if paths:
        best_path = paths[0]
        if len(best_path.version_names) >= 2:
            chain = " → ".join(best_path.version_names)
            findings.append(f"最可能的传播链路: {chain}")

    version_count = len(set(v for p in paths for v in p.version_names))
    findings.append(f"涉及 {version_count} 个版本")

    return findings


def generate_report_content(
    db: Session,
    project_id: int,
    analysis_result: schemas.TransmissionAnalysisResult,
    created_by: str = None
) -> str:
    target_diff = crud.get_diff(db, analysis_result.target_diff_id)
    project = crud.get_project(db, project_id)

    sections = []

    sections.append("=" * 60)
    sections.append("异文传播分析报告")
    sections.append("=" * 60)
    sections.append("")

    sections.append("一、基本信息")
    sections.append("-" * 40)
    sections.append(f"项目: {project.name if project else '未知'}")
    sections.append(f"异文ID: {analysis_result.target_diff_id}")
    sections.append(f"异文文本: {target_diff.text if target_diff else '未知'}")
    sections.append(f"异文类型: {target_diff.diff_type if target_diff else '未知'}")
    sections.append(f"分析方法: {analysis_result.analysis_method}")
    sections.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sections.append("")

    sections.append("二、分析结论")
    sections.append("-" * 40)
    sections.append(f"最可能成因: {get_cause_label(analysis_result.likely_cause)}")
    sections.append(f"综合置信度: {analysis_result.confidence}%")
    sections.append("")

    sections.append("三、主要发现")
    sections.append("-" * 40)
    for i, finding in enumerate(analysis_result.key_findings, 1):
        sections.append(f"{i}. {finding}")
    sections.append("")

    sections.append("四、传播路径详情")
    sections.append("-" * 40)
    for i, path in enumerate(analysis_result.transmission_paths[:10], 1):
        chain = " → ".join(path.version_names)
        sections.append(f"路径 {i}:")
        sections.append(f"  链路: {chain}")
        sections.append(f"  类型: {get_path_type_label(path.path_type)}")
        sections.append(f"  权重: {path.total_weight}")
        sections.append(f"  证据数: {path.evidence_count}")
        sections.append("")

    sections.append("五、建议")
    sections.append("-" * 40)
    suggestions = generate_suggestions(analysis_result, target_diff)
    for i, suggestion in enumerate(suggestions, 1):
        sections.append(f"{i}. {suggestion}")
    sections.append("")

    sections.append("=" * 60)
    sections.append("报告结束")
    sections.append("=" * 60)

    return "\n".join(sections)


def get_cause_label(cause: str) -> str:
    labels = {
        "direct_inheritance": "直接承袭",
        "copy_error": "传抄讹误",
        "version_inheritance": "版本承袭",
        "indirect_transmission": "间接传播",
        "later_revision": "后世改写",
        "uncertain": "不确定",
        "unknown": "未知"
    }
    return labels.get(cause, cause)


def get_path_type_label(path_type: str) -> str:
    labels = {
        "direct_copy": "直接复制",
        "copy_error": "传抄讹误",
        "version_inheritance": "版本承袭",
        "indirect_transmission": "间接传播",
        "unknown": "未知"
    }
    return labels.get(path_type, path_type)


def generate_suggestions(
    analysis_result: schemas.TransmissionAnalysisResult,
    target_diff
) -> List[str]:
    suggestions = []

    if analysis_result.confidence < 60:
        suggestions.append("建议进一步核查相关版本的序跋、凡例等文献，以确定版本源流")
        suggestions.append("建议增加更多版本的比对数据，提高分析的准确性")

    if analysis_result.likely_cause == "copy_error":
        suggestions.append("建议结合字形分析，判断是否为形近而讹")
        suggestions.append("建议参考同书其他版本相同位置的文字，验证讹误的可能性")

    if analysis_result.likely_cause == "direct_inheritance":
        suggestions.append("可将该异文作为版本谱系划分的重要依据")
        suggestions.append("建议进一步考察该版本系统的整体文字特征")

    if analysis_result.likely_cause == "version_inheritance":
        suggestions.append("建议梳理版本间的承袭关系，构建完整的版本谱系")
        suggestions.append("可结合其他异文的传播特征，综合判断版本关系")

    if not suggestions:
        suggestions.append("建议结合校勘实践，综合判断该异文的处理方式")

    return suggestions


@router.get("/projects/{project_id}/transmission", response_class=HTMLResponse)
async def transmission_page(
    request: Request,
    project_id: int,
    diff_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    diffs = crud.get_diffs_by_project(db, project_id)
    reports = crud.get_transmission_reports_by_project(db, project_id)
    lineages = crud.get_version_lineages_by_project(db, project_id)

    analysis_result = None
    if diff_id:
        try:
            analysis_result = analyze_transmission_paths(db, project_id, diff_id)
        except Exception as e:
            analysis_result = None

    return templates.TemplateResponse("transmission_analysis.html", {
        "request": request,
        "project": project,
        "diffs": diffs,
        "reports": reports,
        "lineages": lineages,
        "selected_diff_id": diff_id,
        "analysis_result": analysis_result,
        "get_cause_label": get_cause_label,
        "get_path_type_label": get_path_type_label
    })


@router.get("/api/projects/{project_id}/transmission/analyze")
async def analyze_transmission_api(
    project_id: int,
    diff_id: int,
    max_depth: int = 5,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = analyze_transmission_paths(db, project_id, diff_id, max_depth)

    return result


@router.post("/api/projects/{project_id}/transmission/reports")
async def create_transmission_report_api(
    project_id: int,
    diff_id: int,
    created_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    target_diff = crud.get_diff(db, diff_id)
    if not target_diff:
        raise HTTPException(status_code=404, detail="异文不存在")

    analysis_result = analyze_transmission_paths(db, project_id, diff_id)
    content = generate_report_content(db, project_id, analysis_result, created_by)

    summary = f"异文ID{diff_id}的传播分析报告。成因: {get_cause_label(analysis_result.likely_cause)}, 置信度: {analysis_result.confidence}%"

    title = f"异文{diff_id}传播分析报告"
    if target_diff.text:
        title = f"异文「{target_diff.text}」传播分析报告"

    report_data = schemas.TransmissionReportCreate(
        project_id=project_id,
        title=title,
        report_type="diff_transmission",
        target_diff_id=diff_id,
        content=content,
        summary=summary,
        analysis_method=analysis_result.analysis_method,
        findings_count=len(analysis_result.key_findings),
        created_by=created_by
    )

    report = crud.create_transmission_report(db, report_data)

    return {
        "status": "success",
        "message": "报告生成成功",
        "report_id": report.id,
        "report": report
    }


@router.get("/api/projects/{project_id}/transmission/reports")
async def list_transmission_reports_api(
    project_id: int,
    report_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    reports = crud.get_transmission_reports_by_project(db, project_id, report_type)

    return {
        "project_id": project_id,
        "report_type": report_type,
        "count": len(reports),
        "reports": reports
    }


@router.get("/api/projects/{project_id}/transmission/reports/{report_id}")
async def get_transmission_report_api(
    project_id: int,
    report_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    report = crud.get_transmission_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return report


@router.delete("/api/projects/{project_id}/transmission/reports/{report_id}")
async def delete_transmission_report_api(
    project_id: int,
    report_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    report = crud.delete_transmission_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return {"status": "success", "message": "报告已删除"}


@router.get("/projects/{project_id}/transmission/reports/{report_id}", response_class=HTMLResponse)
async def view_transmission_report_page(
    request: Request,
    project_id: int,
    report_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    report = crud.get_transmission_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return templates.TemplateResponse("transmission_report.html", {
        "request": request,
        "project": project,
        "report": report
    })
