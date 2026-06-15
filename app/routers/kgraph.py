from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import json
from datetime import datetime

from app.database import get_db
from app import crud, schemas, models

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/projects/{project_id}/graph", response_class=HTMLResponse)
async def graph_page(
    request: Request,
    project_id: int,
    node_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    graph_data = crud.get_graph_data(db, project_id)
    stats = crud.get_project_stats(db, project_id)

    node_type_counts = {}
    for node in graph_data.nodes:
        node_type_counts[node.node_type] = node_type_counts.get(node.node_type, 0) + 1

    edge_type_counts = {}
    for edge in graph_data.edges:
        edge_type_counts[edge.edge_type] = edge_type_counts.get(edge.edge_type, 0) + 1

    return templates.TemplateResponse("knowledge_graph.html", {
        "request": request,
        "project": project,
        "graph_data": graph_data,
        "stats": stats,
        "node_type_counts": node_type_counts,
        "edge_type_counts": edge_type_counts,
        "node_types": models.GRAPH_NODE_TYPES,
        "edge_types": models.GRAPH_EDGE_TYPES,
        "diff_relation_types": models.DIFF_RELATION_TYPES
    })


@router.get("/api/projects/{project_id}/graph")
async def get_graph_api(
    project_id: int,
    node_type: Optional[str] = None,
    edge_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    nodes = crud.get_graph_nodes_by_project(db, project_id, node_type)
    edges = crud.get_graph_edges_by_project(db, project_id, edge_type)

    nodes_data = []
    for node in nodes:
        nodes_data.append({
            "id": node.id,
            "type": node.node_type,
            "ref_id": node.ref_id,
            "label": node.label,
            "description": node.description,
            "properties": json.loads(node.properties) if node.properties else {}
        })

    edges_data = []
    for edge in edges:
        edges_data.append({
            "id": edge.id,
            "source": edge.source_id,
            "target": edge.target_id,
            "type": edge.edge_type,
            "weight": edge.weight,
            "properties": json.loads(edge.properties) if edge.properties else {}
        })

    return {
        "project_id": project_id,
        "nodes": nodes_data,
        "edges": edges_data,
        "node_count": len(nodes_data),
        "edge_count": len(edges_data)
    }


@router.post("/api/projects/{project_id}/graph/build")
async def build_graph_api(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    graph_data = crud.build_graph_from_existing_data(db, project_id)

    return {
        "status": "success",
        "message": "知识图谱构建完成",
        "node_count": len(graph_data.nodes),
        "edge_count": len(graph_data.edges)
    }


@router.post("/api/projects/{project_id}/graph/nodes")
async def create_graph_node_api(
    project_id: int,
    node_data: schemas.GraphNodeBase,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    create_data = schemas.GraphNodeCreate(
        project_id=project_id,
        **node_data.model_dump()
    )
    node = crud.create_graph_node(db, create_data)

    return node


@router.get("/api/projects/{project_id}/graph/nodes/{node_id}")
async def get_graph_node_api(
    project_id: int,
    node_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    node = crud.get_graph_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    return node


@router.delete("/api/projects/{project_id}/graph/nodes/{node_id}")
async def delete_graph_node_api(
    project_id: int,
    node_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    node = crud.delete_graph_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    return {"status": "success", "message": "节点已删除"}


@router.post("/api/projects/{project_id}/graph/edges")
async def create_graph_edge_api(
    project_id: int,
    edge_data: schemas.GraphEdgeBase,
    source_id: int,
    target_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    create_data = schemas.GraphEdgeCreate(
        project_id=project_id,
        source_id=source_id,
        target_id=target_id,
        **edge_data.model_dump()
    )
    edge = crud.create_graph_edge(db, create_data)

    return edge


@router.delete("/api/projects/{project_id}/graph/edges/{edge_id}")
async def delete_graph_edge_api(
    project_id: int,
    edge_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    edge = crud.delete_graph_edge(db, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="关系不存在")

    return {"status": "success", "message": "关系已删除"}


@router.get("/api/projects/{project_id}/diffs/{diff_id}/graph-detail")
async def get_diff_graph_detail_api(
    project_id: int,
    diff_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    detail = crud.get_diff_graph_detail(db, diff_id)
    if not detail:
        raise HTTPException(status_code=404, detail="异文不存在")

    return detail


@router.get("/api/projects/{project_id}/diffs/distribution")
async def get_diff_distribution_api(
    project_id: int,
    diff_text: Optional[str] = None,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    distribution = crud.get_diff_distribution_by_versions(db, project_id, diff_text)

    return {
        "project_id": project_id,
        "diff_text": diff_text,
        "distribution": distribution
    }


@router.get("/projects/{project_id}/diff-relations", response_class=HTMLResponse)
async def diff_relations_page(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    relations = crud.get_diff_relations_by_project(db, project_id)
    diffs = crud.get_diffs_by_project(db, project_id)

    return templates.TemplateResponse("diff_relations.html", {
        "request": request,
        "project": project,
        "relations": relations,
        "diffs": diffs,
        "relation_types": models.DIFF_RELATION_TYPES
    })


@router.post("/api/projects/{project_id}/diff-relations")
async def create_diff_relation_api(
    project_id: int,
    relation_data: schemas.DiffRelationBase,
    source_diff_id: int,
    target_diff_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    source_diff = crud.get_diff(db, source_diff_id)
    target_diff = crud.get_diff(db, target_diff_id)
    if not source_diff or not target_diff:
        raise HTTPException(status_code=404, detail="异文不存在")

    create_data = schemas.DiffRelationCreate(
        project_id=project_id,
        source_diff_id=source_diff_id,
        target_diff_id=target_diff_id,
        **relation_data.model_dump()
    )
    relation = crud.create_diff_relation(db, create_data)

    return relation


@router.delete("/api/projects/{project_id}/diff-relations/{relation_id}")
async def delete_diff_relation_api(
    project_id: int,
    relation_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    relation = crud.delete_diff_relation(db, relation_id)
    if not relation:
        raise HTTPException(status_code=404, detail="关联不存在")

    return {"status": "success", "message": "关联已删除"}


@router.get("/projects/{project_id}/version-lineage", response_class=HTMLResponse)
async def version_lineage_page(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    lineages = crud.get_version_lineages_by_project(db, project_id)
    versions = crud.get_versions_by_project(db, project_id)

    lineage_data = []
    for lineage in lineages:
        parent = crud.get_version(db, lineage.parent_version_id)
        child = crud.get_version(db, lineage.child_version_id)
        lineage_data.append({
            "id": lineage.id,
            "parent_name": parent.name if parent else "未知",
            "child_name": child.name if child else "未知",
            "relation_type": lineage.relation_type,
            "description": lineage.description,
            "confidence": lineage.confidence,
            "evidence": lineage.evidence
        })

    return templates.TemplateResponse("version_lineage.html", {
        "request": request,
        "project": project,
        "lineages": lineage_data,
        "versions": versions
    })


@router.post("/api/projects/{project_id}/version-lineage")
async def create_version_lineage_api(
    project_id: int,
    lineage_data: schemas.VersionLineageBase,
    parent_version_id: int,
    child_version_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if parent_version_id == child_version_id:
        raise HTTPException(status_code=400, detail="父版本和子版本不能相同")

    create_data = schemas.VersionLineageCreate(
        project_id=project_id,
        parent_version_id=parent_version_id,
        child_version_id=child_version_id,
        **lineage_data.model_dump()
    )
    lineage = crud.create_version_lineage(db, create_data)

    return lineage


@router.delete("/api/projects/{project_id}/version-lineage/{lineage_id}")
async def delete_version_lineage_api(
    project_id: int,
    lineage_id: int,
    db: Session = Depends(get_db)
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    lineage = crud.delete_version_lineage(db, lineage_id)
    if not lineage:
        raise HTTPException(status_code=404, detail="谱系关系不存在")

    return {"status": "success", "message": "谱系关系已删除"}
