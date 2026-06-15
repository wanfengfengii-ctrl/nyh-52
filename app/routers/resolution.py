from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os
from datetime import datetime

from app.database import get_db
from app import crud, schemas
from app.text_alignment import DIFF_TYPE_LABELS, DIFF_TYPE_COLORS

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/projects/{project_id}/proposals", response_class=HTMLResponse)
async def proposals_list(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    diffs = crud.get_diffs_by_project(db, project_id)
    proposals_data = []
    for diff in diffs:
        proposals = crud.get_proposals_by_diff(db, diff.id)
        if proposals:
            version = crud.get_version(db, diff.version_id)
            passage = crud.get_passage(db, diff.passage_id)
            for p in proposals:
                vote_summary = crud.get_vote_summary(db, p.id)
                proposals_data.append({
                    "proposal": p,
                    "diff": diff,
                    "version": version,
                    "passage": passage,
                    "vote_summary": vote_summary
                })
    
    return templates.TemplateResponse("proposals_list.html", {
        "request": request,
        "project": project,
        "proposals_data": proposals_data
    })


@router.get("/projects/{project_id}/collaboration/{diff_id}", response_class=HTMLResponse)
async def collaboration_page(
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
    
    version = crud.get_version(db, diff.version_id)
    passage = crud.get_passage(db, diff.passage_id)
    proposals = crud.get_proposals_by_diff(db, diff_id)
    discussions = crud.get_discussions_by_diff(db, diff_id)
    
    proposals_with_details = []
    for p in proposals:
        vote_summary = crud.get_vote_summary(db, p.id)
        citations = crud.get_citations_by_proposal(db, p.id)
        review_records = crud.get_review_records_by_proposal(db, p.id)
        proposals_with_details.append({
            "proposal": p,
            "vote_summary": vote_summary,
            "citations": citations,
            "review_records": review_records
        })
    
    diff_label = DIFF_TYPE_LABELS.get(diff.diff_type, diff.diff_type)
    diff_color = DIFF_TYPE_COLORS.get(diff.diff_type, "#333")
    
    error = request.query_params.get("error", None)
    success = request.query_params.get("success", None)
    
    return templates.TemplateResponse("collaboration.html", {
        "request": request,
        "project": project,
        "diff": diff,
        "version": version,
        "passage": passage,
        "proposals_with_details": proposals_with_details,
        "discussions": discussions,
        "diff_label": diff_label,
        "diff_color": diff_color,
        "error": error,
        "success": success
    })


@router.post("/projects/{project_id}/collaboration/{diff_id}/proposals")
async def create_proposal(
    request: Request,
    project_id: int,
    diff_id: int,
    author: str = Form(...),
    title: str = Form(...),
    proposed_text: str = Form(...),
    rationale: str = Form(...),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    diff = crud.get_diff(db, diff_id)
    if not diff:
        raise HTTPException(status_code=404, detail="差异不存在")
    
    proposal_data = schemas.CollationProposalCreate(
        diff_id=diff_id,
        author=author,
        title=title,
        proposed_text=proposed_text,
        rationale=rationale
    )
    crud.create_proposal(db, proposal_data)
    
    return RedirectResponse(
        f"/projects/{project_id}/collaboration/{diff_id}?success=校勘方案已提交",
        status_code=303
    )


@router.post("/projects/{project_id}/collaboration/{diff_id}/proposals/{proposal_id}/accept")
async def accept_proposal(
    request: Request,
    project_id: int,
    diff_id: int,
    proposal_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    proposal = crud.get_proposal(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="方案不存在")
    
    crud.accept_proposal(db, proposal_id)
    crud.update_diff_status(db, diff_id, "finalized")
    
    return RedirectResponse(
        f"/projects/{project_id}/collaboration/{diff_id}?success=方案已采纳为最终方案",
        status_code=303
    )


@router.post("/projects/{project_id}/collaboration/{diff_id}/proposals/{proposal_id}/vote")
async def vote_proposal(
    request: Request,
    project_id: int,
    diff_id: int,
    proposal_id: int,
    voter: str = Form(...),
    vote_type: str = Form(...),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    proposal = crud.get_proposal(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="方案不存在")
    
    vote_data = schemas.VoteCreate(
        proposal_id=proposal_id,
        voter=voter,
        vote_type=vote_type,
        comment=comment
    )
    crud.create_vote(db, vote_data)
    
    return RedirectResponse(
        f"/projects/{project_id}/collaboration/{diff_id}#proposal-{proposal_id}",
        status_code=303
    )


@router.post("/projects/{project_id}/collaboration/{diff_id}/proposals/{proposal_id}/citations")
async def add_citation(
    request: Request,
    project_id: int,
    diff_id: int,
    proposal_id: int,
    title: str = Form(...),
    author: Optional[str] = Form(None),
    publication: Optional[str] = Form(None),
    page_info: Optional[str] = Form(None),
    quote_text: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    proposal = crud.get_proposal(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="方案不存在")
    
    citation_data = schemas.LiteratureCitationCreate(
        proposal_id=proposal_id,
        title=title,
        author=author,
        publication=publication,
        page_info=page_info,
        quote_text=quote_text,
        note=note
    )
    crud.create_citation(db, citation_data)
    
    return RedirectResponse(
        f"/projects/{project_id}/collaboration/{diff_id}#proposal-{proposal_id}",
        status_code=303
    )


@router.post("/projects/{project_id}/collaboration/{diff_id}/proposals/{proposal_id}/review")
async def review_proposal(
    request: Request,
    project_id: int,
    diff_id: int,
    proposal_id: int,
    reviewer: str = Form(...),
    review_result: str = Form(...),
    review_comment: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    proposal = crud.get_proposal(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="方案不存在")
    
    review_data = schemas.ReviewRecordCreate(
        proposal_id=proposal_id,
        reviewer=reviewer,
        review_result=review_result,
        review_comment=review_comment
    )
    crud.create_review_record(db, review_data)
    
    return RedirectResponse(
        f"/projects/{project_id}/collaboration/{diff_id}#proposal-{proposal_id}",
        status_code=303
    )


@router.post("/projects/{project_id}/collaboration/{diff_id}/discussions")
async def add_discussion(
    request: Request,
    project_id: int,
    diff_id: int,
    author: str = Form(...),
    content: str = Form(...),
    reply_to_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    diff = crud.get_diff(db, diff_id)
    if not diff:
        raise HTTPException(status_code=404, detail="差异不存在")
    
    message_data = schemas.DiscussionMessageCreate(
        diff_id=diff_id,
        author=author,
        content=content,
        reply_to_id=reply_to_id
    )
    crud.create_discussion_message(db, message_data)
    
    return RedirectResponse(
        f"/projects/{project_id}/collaboration/{diff_id}#discussions",
        status_code=303
    )


@router.get("/projects/{project_id}/recommended", response_class=HTMLResponse)
async def recommended_texts_page(
    request: Request,
    project_id: int,
    volume_no: Optional[int] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    versions = crud.get_versions_by_project(db, project_id)
    if not versions:
        raise HTTPException(status_code=400, detail="请先添加版本")
    
    base_version = versions[0]
    volumes = crud.get_volumes_by_version(db, base_version.id)
    
    volume_progress = crud.get_volume_progress(db, project_id)
    
    recommended_texts = []
    if volume_no is not None:
        recommended_texts = crud.get_recommended_texts_by_volume(db, project_id, volume_no)
    
    stats = crud.get_project_stats(db, project_id)
    
    return templates.TemplateResponse("recommended_texts.html", {
        "request": request,
        "project": project,
        "volumes": volumes,
        "selected_volume": volume_no,
        "volume_progress": volume_progress,
        "recommended_texts": recommended_texts,
        "base_version": base_version,
        "stats": stats
    })


@router.get("/projects/{project_id}/recommended/generate", response_class=HTMLResponse)
async def generate_recommended_page(
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
    if not versions or len(versions) < 2:
        raise HTTPException(status_code=400, detail="请至少添加2个版本")
    
    base_version = versions[0]
    all_volumes = crud.get_volumes_by_version(db, base_version.id)
    
    max_paragraph_count = 0
    if volume_no is not None:
        passages = crud.get_passages_by_version_volume(db, base_version.id, volume_no)
        if passages:
            max_paragraph_count = max(p.paragraph_no for p in passages)
    
    return templates.TemplateResponse("generate_recommended.html", {
        "request": request,
        "project": project,
        "versions": versions,
        "volumes": all_volumes,
        "selected_volume": volume_no,
        "selected_paragraph": paragraph_no,
        "base_version": base_version,
        "max_paragraph_count": max_paragraph_count
    })


@router.post("/projects/{project_id}/recommended/generate")
async def generate_recommended_text(
    request: Request,
    project_id: int,
    volume_no: int = Form(...),
    paragraph_no: int = Form(...),
    base_version_id: int = Form(...),
    generated_by: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    base_version = crud.get_version(db, base_version_id)
    if not base_version:
        raise HTTPException(status_code=404, detail="基础版本不存在")
    
    base_passage = crud.get_passage_by_location(db, base_version_id, volume_no, paragraph_no)
    if not base_passage:
        return RedirectResponse(
            f"/projects/{project_id}/recommended/generate?volume_no={volume_no}&paragraph_no={paragraph_no}&error=基础版本该段落不存在",
            status_code=303
        )
    
    recommended_content = base_passage.content
    
    diffs = crud.get_diffs_by_passage(db, base_passage.id)
    accepted_proposals_data = []
    
    for diff in diffs:
        proposals = crud.get_proposals_by_diff(db, diff.id)
        accepted = next((p for p in proposals if p.is_accepted), None)
        if accepted:
            accepted_proposals_data.append({
                "diff": diff,
                "proposal": accepted
            })
    
    existing = crud.get_recommended_text(db, project_id, volume_no, paragraph_no)
    if existing:
        rt_update = schemas.RecommendedTextUpdate(
            content=recommended_content,
            status="draft"
        )
        rt = crud.update_recommended_text(db, existing.id, rt_update)
    else:
        rt_data = schemas.RecommendedTextCreate(
            project_id=project_id,
            volume_no=volume_no,
            paragraph_no=paragraph_no,
            content=recommended_content,
            status="draft",
            base_version_id=base_version_id,
            generated_by=generated_by
        )
        rt = crud.create_recommended_text(db, rt_data)
    
    from app.models import RecommendedTextEvidence
    from app import models
    db.query(models.RecommendedTextEvidence).filter(
        models.RecommendedTextEvidence.recommended_text_id == rt.id
    ).delete()
    db.commit()
    
    for item in accepted_proposals_data:
        diff = item["diff"]
        proposal = item["proposal"]
        diff_version = crud.get_version(db, diff.version_id)
        
        evidence_data = schemas.RecommendedTextEvidenceCreate(
            recommended_text_id=rt.id,
            diff_id=diff.id,
            proposal_id=proposal.id,
            evidence_type="accepted_proposal",
            description=f"采纳方案：{proposal.title}，作者：{proposal.author}",
            source_version_name=diff_version.name if diff_version else None
        )
        crud.create_recommended_text_evidence(db, evidence_data)
    
    return RedirectResponse(
        f"/projects/{project_id}/recommended?volume_no={volume_no}&success=推荐文本已生成",
        status_code=303
    )


@router.post("/projects/{project_id}/recommended/generate-volume")
async def generate_volume_recommended(
    request: Request,
    project_id: int,
    volume_no: int = Form(...),
    base_version_id: int = Form(...),
    generated_by: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    base_version = crud.get_version(db, base_version_id)
    if not base_version:
        raise HTTPException(status_code=404, detail="基础版本不存在")
    
    passages = crud.get_passages_by_version_volume(db, base_version_id, volume_no)
    
    generated_count = 0
    for passage in passages:
        existing = crud.get_recommended_text(db, project_id, volume_no, passage.paragraph_no)
        if existing:
            continue
        
        rt_data = schemas.RecommendedTextCreate(
            project_id=project_id,
            volume_no=volume_no,
            paragraph_no=passage.paragraph_no,
            content=passage.content,
            status="draft",
            base_version_id=base_version_id,
            generated_by=generated_by
        )
        crud.create_recommended_text(db, rt_data)
        generated_count += 1
    
    return RedirectResponse(
        f"/projects/{project_id}/recommended?volume_no={volume_no}&success=已生成{generated_count}段推荐文本",
        status_code=303
    )


@router.post("/projects/{project_id}/recommended/{rt_id}/review")
async def review_recommended_text(
    request: Request,
    project_id: int,
    rt_id: int,
    reviewed_by: str = Form(...),
    action: str = Form(...),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    rt = crud.get_recommended_text_by_id(db, rt_id)
    if not rt:
        raise HTTPException(status_code=404, detail="推荐文本不存在")
    
    if action == "approve":
        rt_update = schemas.RecommendedTextUpdate(
            status="reviewed",
            reviewed_by=reviewed_by
        )
        success_msg = "推荐文本已审核通过"
    elif action == "reject":
        rt_update = schemas.RecommendedTextUpdate(
            status="draft",
            reviewed_by=None
        )
        success_msg = "推荐文本已退回草稿"
    else:
        return RedirectResponse(
            f"/projects/{project_id}/recommended?volume_no={rt.volume_no}&error=无效操作",
            status_code=303
        )
    
    crud.update_recommended_text(db, rt_id, rt_update)
    
    return RedirectResponse(
        f"/projects/{project_id}/recommended?volume_no={rt.volume_no}&success={success_msg}",
        status_code=303
    )


@router.post("/projects/{project_id}/recommended/{rt_id}/edit")
async def edit_recommended_text(
    request: Request,
    project_id: int,
    rt_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    rt = crud.get_recommended_text_by_id(db, rt_id)
    if not rt:
        raise HTTPException(status_code=404, detail="推荐文本不存在")
    
    rt_update = schemas.RecommendedTextUpdate(
        content=content,
        status="draft"
    )
    crud.update_recommended_text(db, rt_id, rt_update)
    
    return RedirectResponse(
        f"/projects/{project_id}/recommended?volume_no={rt.volume_no}&success=推荐文本已更新",
        status_code=303
    )


@router.get("/projects/{project_id}/recommended/preview", response_class=HTMLResponse)
async def preview_recommended(
    request: Request,
    project_id: int,
    volume_no: Optional[int] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    versions = crud.get_versions_by_project(db, project_id)
    if not versions:
        raise HTTPException(status_code=400, detail="请先添加版本")
    
    base_version = versions[0]
    volumes = crud.get_volumes_by_version(db, base_version.id)
    
    preview_data = []
    if volume_no is not None:
        passages = crud.get_passages_by_version_volume(db, base_version.id, volume_no)
        for passage in passages:
            rt = crud.get_recommended_text(db, project_id, volume_no, passage.paragraph_no)
            if rt:
                evidences = crud.get_evidences_by_recommended_text(db, rt.id)
                preview_data.append({
                    "paragraph_no": passage.paragraph_no,
                    "original": passage.content,
                    "recommended": rt,
                    "evidences": evidences
                })
            else:
                preview_data.append({
                    "paragraph_no": passage.paragraph_no,
                    "original": passage.content,
                    "recommended": None,
                    "evidences": []
                })
    
    return templates.TemplateResponse("recommended_preview.html", {
        "request": request,
        "project": project,
        "volumes": volumes,
        "selected_volume": volume_no,
        "preview_data": preview_data,
        "base_version": base_version
    })
