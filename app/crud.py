from sqlalchemy.orm import Session
from app import models, schemas
from typing import List, Optional


def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).order_by(models.Project.created_at.desc()).offset(skip).limit(limit).all()


def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_versions_by_project(db: Session, project_id: int):
    return db.query(models.Version).filter(models.Version.project_id == project_id).all()


def get_version(db: Session, version_id: int):
    return db.query(models.Version).filter(models.Version.id == version_id).first()


def get_version_by_name(db: Session, project_id: int, name: str):
    return db.query(models.Version).filter(
        models.Version.project_id == project_id,
        models.Version.name == name
    ).first()


def create_version(db: Session, version: schemas.VersionCreate):
    db_version = models.Version(**version.model_dump())
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version


def get_passages_by_version(db: Session, version_id: int):
    return db.query(models.Passage).filter(
        models.Passage.version_id == version_id
    ).order_by(models.Passage.volume_no, models.Passage.paragraph_no).all()


def get_passages_by_version_volume(db: Session, version_id: int, volume_no: int):
    return db.query(models.Passage).filter(
        models.Passage.version_id == version_id,
        models.Passage.volume_no == volume_no
    ).order_by(models.Passage.paragraph_no).all()


def get_passage(db: Session, passage_id: int):
    return db.query(models.Passage).filter(models.Passage.id == passage_id).first()


def get_passage_by_location(db: Session, version_id: int, volume_no: int, paragraph_no: int):
    return db.query(models.Passage).filter(
        models.Passage.version_id == version_id,
        models.Passage.volume_no == volume_no,
        models.Passage.paragraph_no == paragraph_no
    ).first()


def get_passage_paragraph_numbers(db: Session, version_id: int, volume_no: int):
    passages = db.query(models.Passage).filter(
        models.Passage.version_id == version_id,
        models.Passage.volume_no == volume_no
    ).order_by(models.Passage.paragraph_no).all()
    return [p.paragraph_no for p in passages]


def create_passage(db: Session, passage: schemas.PassageCreate):
    db_passage = models.Passage(**passage.model_dump())
    db.add(db_passage)
    db.commit()
    db.refresh(db_passage)
    return db_passage


def update_passage(db: Session, passage_id: int, passage_update: schemas.PassageUpdate):
    db_passage = db.query(models.Passage).filter(models.Passage.id == passage_id).first()
    if db_passage:
        for key, value in passage_update.model_dump().items():
            setattr(db_passage, key, value)
        db.commit()
        db.refresh(db_passage)
    return db_passage


def delete_passage(db: Session, passage_id: int):
    db_passage = db.query(models.Passage).filter(models.Passage.id == passage_id).first()
    if db_passage:
        db.delete(db_passage)
        db.commit()
    return db_passage


def get_volumes_by_version(db: Session, version_id: int):
    passages = db.query(models.Passage).filter(
        models.Passage.version_id == version_id
    ).all()
    volumes = sorted(set(p.volume_no for p in passages))
    return volumes


def get_diffs_by_project(db: Session, project_id: int):
    return db.query(models.Diff).filter(models.Diff.project_id == project_id).all()


def get_diffs_by_passage(db: Session, passage_id: int):
    return db.query(models.Diff).filter(models.Diff.passage_id == passage_id).all()


def get_diff(db: Session, diff_id: int):
    return db.query(models.Diff).filter(models.Diff.id == diff_id).first()


def create_diff(db: Session, diff: schemas.DiffCreate):
    db_diff = models.Diff(**diff.model_dump())
    db.add(db_diff)
    db.commit()
    db.refresh(db_diff)
    return db_diff


def update_diff_status(db: Session, diff_id: int, status: str):
    db_diff = db.query(models.Diff).filter(models.Diff.id == diff_id).first()
    if db_diff:
        db_diff.status = status
        db.commit()
        db.refresh(db_diff)
    return db_diff


def delete_diffs_by_passage(db: Session, passage_id: int):
    db.query(models.Diff).filter(models.Diff.passage_id == passage_id).delete()
    db.commit()


def get_collation_notes_by_diff(db: Session, diff_id: int):
    return db.query(models.CollationNote).filter(
        models.CollationNote.diff_id == diff_id
    ).order_by(models.CollationNote.created_at.desc()).all()


def get_collation_note(db: Session, note_id: int):
    return db.query(models.CollationNote).filter(models.CollationNote.id == note_id).first()


def create_collation_note(db: Session, note: schemas.CollationNoteCreate):
    db_note = models.CollationNote(**note.model_dump())
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


def update_collation_note_final(db: Session, note_id: int, is_final: bool):
    db_note = db.query(models.CollationNote).filter(models.CollationNote.id == note_id).first()
    if db_note:
        db_note.is_final = is_final
        if is_final:
            db_note.needs_review = False
        db.commit()
        db.refresh(db_note)
    return db_note


def mark_notes_for_review_by_passage(db: Session, passage_id: int):
    diffs = db.query(models.Diff).filter(models.Diff.passage_id == passage_id).all()
    for diff in diffs:
        notes = db.query(models.CollationNote).filter(
            models.CollationNote.diff_id == diff.id,
            models.CollationNote.is_final == True
        ).all()
        for note in notes:
            note.needs_review = True
            note.is_final = False
        if notes:
            diff.status = "reviewed"
    db.commit()


def backup_notes_for_passage(db: Session, passage_id: int):
    diffs = db.query(models.Diff).filter(models.Diff.passage_id == passage_id).all()
    backup = []
    for diff in diffs:
        notes = db.query(models.CollationNote).filter(
            models.CollationNote.diff_id == diff.id
        ).all()
        for note in notes:
            backup.append({
                "diff_type": diff.diff_type,
                "position_start": diff.position_start,
                "position_end": diff.position_end,
                "text": diff.text,
                "reference_text": diff.reference_text,
                "author": note.author,
                "content": note.content,
                "evidence": note.evidence,
                "was_final": note.is_final,
                "needs_review": True,
                "created_at": note.created_at
            })
    return backup


def restore_notes_to_new_diffs(db: Session, passage_id: int, notes_backup: list):
    if not notes_backup:
        return
    
    new_diffs = db.query(models.Diff).filter(models.Diff.passage_id == passage_id).all()
    
    has_final_notes = False
    for old_note in notes_backup:
        matched_diff = None
        for d in new_diffs:
            if (d.diff_type == old_note["diff_type"] and
                d.position_start == old_note["position_start"] and
                d.position_end == old_note["position_end"]):
                matched_diff = d
                break
        
        if matched_diff is None:
            for d in new_diffs:
                if d.diff_type == old_note["diff_type"]:
                    matched_diff = d
                    break
        
        if matched_diff:
            new_note = models.CollationNote(
                diff_id=matched_diff.id,
                author=old_note["author"],
                content=old_note["content"],
                evidence=old_note["evidence"],
                is_final=False,
                needs_review=True,
                created_at=old_note["created_at"]
            )
            db.add(new_note)
            if old_note["was_final"]:
                has_final_notes = True
    
    if has_final_notes:
        for d in new_diffs:
            if d.status == "finalized":
                d.status = "reviewed"
    
    db.commit()


def get_diffs_by_location(db: Session, project_id: int, volume_no: int, paragraph_no: int):
    from app.models import Passage, Diff
    passages = db.query(Passage).filter(
        Passage.volume_no == volume_no,
        Passage.paragraph_no == paragraph_no
    ).all()
    passage_ids = [p.id for p in passages]
    if not passage_ids:
        return []
    return db.query(Diff).filter(
        Diff.passage_id.in_(passage_ids)
    ).all()


def get_project_stats(db: Session, project_id: int) -> schemas.ProjectStats:
    versions = get_versions_by_project(db, project_id)
    total_versions = len(versions)
    
    total_passages = 0
    for v in versions:
        total_passages += len(get_passages_by_version(db, v.id))
    
    diffs = get_diffs_by_project(db, project_id)
    total_diffs = len(diffs)
    pending_diffs = sum(1 for d in diffs if d.status == "pending")
    reviewed_diffs = sum(1 for d in diffs if d.status == "reviewed")
    finalized_diffs = sum(1 for d in diffs if d.status == "finalized")
    
    progress_percent = 0.0
    if total_diffs > 0:
        progress_percent = round((finalized_diffs / total_diffs) * 100, 1)
    
    recommended_texts = get_recommended_texts_by_project(db, project_id)
    recommended_paragraphs = len(recommended_texts)
    reviewed_recommended = sum(1 for rt in recommended_texts if rt.status == "reviewed")
    
    return schemas.ProjectStats(
        total_versions=total_versions,
        total_passages=total_passages,
        total_diffs=total_diffs,
        pending_diffs=pending_diffs,
        reviewed_diffs=reviewed_diffs,
        finalized_diffs=finalized_diffs,
        progress_percent=progress_percent,
        recommended_paragraphs=recommended_paragraphs,
        reviewed_recommended=reviewed_recommended
    )


def get_proposals_by_diff(db: Session, diff_id: int):
    from app.models import CollationProposal
    return db.query(CollationProposal).filter(
        CollationProposal.diff_id == diff_id
    ).order_by(CollationProposal.created_at.desc()).all()


def get_proposal(db: Session, proposal_id: int):
    from app.models import CollationProposal
    return db.query(CollationProposal).filter(CollationProposal.id == proposal_id).first()


def create_proposal(db: Session, proposal: schemas.CollationProposalCreate):
    from app.models import CollationProposal
    db_proposal = CollationProposal(**proposal.model_dump())
    db.add(db_proposal)
    db.commit()
    db.refresh(db_proposal)
    return db_proposal


def update_proposal(db: Session, proposal_id: int, proposal_update: schemas.CollationProposalUpdate):
    from app.models import CollationProposal
    db_proposal = db.query(CollationProposal).filter(CollationProposal.id == proposal_id).first()
    if db_proposal:
        update_data = proposal_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_proposal, key, value)
        db.commit()
        db.refresh(db_proposal)
    return db_proposal


def accept_proposal(db: Session, proposal_id: int):
    from app.models import CollationProposal
    db_proposal = db.query(CollationProposal).filter(CollationProposal.id == proposal_id).first()
    if db_proposal:
        db.query(CollationProposal).filter(
            CollationProposal.diff_id == db_proposal.diff_id
        ).update({CollationProposal.is_accepted: False})
        db_proposal.is_accepted = True
        db.commit()
        db.refresh(db_proposal)
    return db_proposal


def delete_proposal(db: Session, proposal_id: int):
    from app.models import CollationProposal
    db_proposal = db.query(CollationProposal).filter(CollationProposal.id == proposal_id).first()
    if db_proposal:
        db.delete(db_proposal)
        db.commit()
    return db_proposal


def create_citation(db: Session, citation: schemas.LiteratureCitationCreate):
    from app.models import LiteratureCitation
    db_citation = LiteratureCitation(**citation.model_dump())
    db.add(db_citation)
    db.commit()
    db.refresh(db_citation)
    return db_citation


def get_citations_by_proposal(db: Session, proposal_id: int):
    from app.models import LiteratureCitation
    return db.query(LiteratureCitation).filter(
        LiteratureCitation.proposal_id == proposal_id
    ).order_by(LiteratureCitation.created_at.desc()).all()


def delete_citation(db: Session, citation_id: int):
    from app.models import LiteratureCitation
    db_citation = db.query(LiteratureCitation).filter(LiteratureCitation.id == citation_id).first()
    if db_citation:
        db.delete(db_citation)
        db.commit()
    return db_citation


def create_vote(db: Session, vote: schemas.VoteCreate):
    from app.models import Vote
    existing = db.query(Vote).filter(
        Vote.proposal_id == vote.proposal_id,
        Vote.voter == vote.voter
    ).first()
    if existing:
        existing.vote_type = vote.vote_type
        existing.comment = vote.comment
        db.commit()
        db.refresh(existing)
        return existing
    db_vote = Vote(**vote.model_dump())
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)
    return db_vote


def get_votes_by_proposal(db: Session, proposal_id: int):
    from app.models import Vote
    return db.query(Vote).filter(Vote.proposal_id == proposal_id).all()


def get_vote_summary(db: Session, proposal_id: int) -> schemas.ProposalVoteSummary:
    from app.models import Vote
    votes = db.query(Vote).filter(Vote.proposal_id == proposal_id).all()
    agree = sum(1 for v in votes if v.vote_type == "agree")
    disagree = sum(1 for v in votes if v.vote_type == "disagree")
    abstain = sum(1 for v in votes if v.vote_type == "abstain")
    return schemas.ProposalVoteSummary(
        proposal_id=proposal_id,
        agree_count=agree,
        disagree_count=disagree,
        abstain_count=abstain,
        total_votes=len(votes)
    )


def delete_vote(db: Session, proposal_id: int, voter: str):
    from app.models import Vote
    db_vote = db.query(Vote).filter(
        Vote.proposal_id == proposal_id,
        Vote.voter == voter
    ).first()
    if db_vote:
        db.delete(db_vote)
        db.commit()
    return db_vote


def get_discussions_by_diff(db: Session, diff_id: int):
    from app.models import DiscussionMessage
    return db.query(DiscussionMessage).filter(
        DiscussionMessage.diff_id == diff_id
    ).order_by(DiscussionMessage.created_at.asc()).all()


def create_discussion_message(db: Session, message: schemas.DiscussionMessageCreate):
    from app.models import DiscussionMessage
    db_message = DiscussionMessage(**message.model_dump())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def get_discussion_message(db: Session, message_id: int):
    from app.models import DiscussionMessage
    return db.query(DiscussionMessage).filter(DiscussionMessage.id == message_id).first()


def delete_discussion_message(db: Session, message_id: int):
    from app.models import DiscussionMessage
    db_message = db.query(DiscussionMessage).filter(DiscussionMessage.id == message_id).first()
    if db_message:
        db.delete(db_message)
        db.commit()
    return db_message


def create_review_record(db: Session, record: schemas.ReviewRecordCreate):
    from app.models import ReviewRecord
    db_record = ReviewRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def get_review_records_by_proposal(db: Session, proposal_id: int):
    from app.models import ReviewRecord
    return db.query(ReviewRecord).filter(
        ReviewRecord.proposal_id == proposal_id
    ).order_by(ReviewRecord.created_at.desc()).all()


def get_recommended_texts_by_project(db: Session, project_id: int):
    from app.models import RecommendedText
    return db.query(RecommendedText).filter(
        RecommendedText.project_id == project_id
    ).order_by(RecommendedText.volume_no, RecommendedText.paragraph_no).all()


def get_recommended_texts_by_volume(db: Session, project_id: int, volume_no: int):
    from app.models import RecommendedText
    return db.query(RecommendedText).filter(
        RecommendedText.project_id == project_id,
        RecommendedText.volume_no == volume_no
    ).order_by(RecommendedText.paragraph_no).all()


def get_recommended_text(db: Session, project_id: int, volume_no: int, paragraph_no: int):
    from app.models import RecommendedText
    return db.query(RecommendedText).filter(
        RecommendedText.project_id == project_id,
        RecommendedText.volume_no == volume_no,
        RecommendedText.paragraph_no == paragraph_no
    ).first()


def get_recommended_text_by_id(db: Session, recommended_text_id: int):
    from app.models import RecommendedText
    return db.query(RecommendedText).filter(RecommendedText.id == recommended_text_id).first()


def create_recommended_text(db: Session, recommended_text: schemas.RecommendedTextCreate):
    from app.models import RecommendedText
    db_rt = RecommendedText(**recommended_text.model_dump())
    db.add(db_rt)
    db.commit()
    db.refresh(db_rt)
    return db_rt


def update_recommended_text(db: Session, recommended_text_id: int, rt_update: schemas.RecommendedTextUpdate):
    from app.models import RecommendedText
    from datetime import datetime
    db_rt = db.query(RecommendedText).filter(RecommendedText.id == recommended_text_id).first()
    if db_rt:
        update_data = rt_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_rt, key, value)
        if "status" in update_data and update_data["status"] == "reviewed":
            db_rt.reviewed_at = datetime.now()
        db.commit()
        db.refresh(db_rt)
    return db_rt


def delete_recommended_text(db: Session, recommended_text_id: int):
    from app.models import RecommendedText
    db_rt = db.query(RecommendedText).filter(RecommendedText.id == recommended_text_id).first()
    if db_rt:
        db.delete(db_rt)
        db.commit()
    return db_rt


def create_recommended_text_evidence(db: Session, evidence: schemas.RecommendedTextEvidenceCreate):
    from app.models import RecommendedTextEvidence
    db_evidence = RecommendedTextEvidence(**evidence.model_dump())
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    return db_evidence


def get_evidences_by_recommended_text(db: Session, recommended_text_id: int):
    from app.models import RecommendedTextEvidence
    return db.query(RecommendedTextEvidence).filter(
        RecommendedTextEvidence.recommended_text_id == recommended_text_id
    ).all()


def get_volume_progress(db: Session, project_id: int) -> list:
    from app.models import RecommendedText, Passage, Version
    versions = get_versions_by_project(db, project_id)
    if not versions:
        return []
    
    base_version = versions[0]
    volumes = get_volumes_by_version(db, base_version.id)
    
    progress_list = []
    for vol in volumes:
        passages = get_passages_by_version_volume(db, base_version.id, vol)
        total_paragraphs = len(passages)
        
        recommended = get_recommended_texts_by_volume(db, project_id, vol)
        recommended_count = len(recommended)
        reviewed_count = sum(1 for rt in recommended if rt.status == "reviewed")
        
        progress_percent = 0.0
        if total_paragraphs > 0:
            progress_percent = round((reviewed_count / total_paragraphs) * 100, 1)
        
        progress_list.append(schemas.VolumeProgress(
            volume_no=vol,
            total_paragraphs=total_paragraphs,
            recommended_count=recommended_count,
            reviewed_count=reviewed_count,
            progress_percent=progress_percent
        ))
    
    return progress_list


def get_graph_nodes_by_project(db: Session, project_id: int, node_type: Optional[str] = None):
    from app.models import GraphNode
    query = db.query(GraphNode).filter(GraphNode.project_id == project_id)
    if node_type:
        query = query.filter(GraphNode.node_type == node_type)
    return query.all()


def get_graph_node(db: Session, node_id: int):
    from app.models import GraphNode
    return db.query(GraphNode).filter(GraphNode.id == node_id).first()


def get_graph_node_by_ref(db: Session, project_id: int, node_type: str, ref_id: int):
    from app.models import GraphNode
    return db.query(GraphNode).filter(
        GraphNode.project_id == project_id,
        GraphNode.node_type == node_type,
        GraphNode.ref_id == ref_id
    ).first()


def create_graph_node(db: Session, node: schemas.GraphNodeCreate):
    from app.models import GraphNode
    existing = get_graph_node_by_ref(db, node.project_id, node.node_type, node.ref_id) if node.ref_id else None
    if existing:
        return existing
    db_node = GraphNode(**node.model_dump())
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node


def update_graph_node(db: Session, node_id: int, label: Optional[str] = None, description: Optional[str] = None):
    from app.models import GraphNode
    db_node = get_graph_node(db, node_id)
    if db_node:
        if label is not None:
            db_node.label = label
        if description is not None:
            db_node.description = description
        db.commit()
        db.refresh(db_node)
    return db_node


def delete_graph_node(db: Session, node_id: int):
    from app.models import GraphNode
    db_node = get_graph_node(db, node_id)
    if db_node:
        db.delete(db_node)
        db.commit()
    return db_node


def get_graph_edges_by_project(db: Session, project_id: int, edge_type: Optional[str] = None):
    from app.models import GraphEdge
    query = db.query(GraphEdge).filter(GraphEdge.project_id == project_id)
    if edge_type:
        query = query.filter(GraphEdge.edge_type == edge_type)
    return query.all()


def get_graph_edge(db: Session, edge_id: int):
    from app.models import GraphEdge
    return db.query(GraphEdge).filter(GraphEdge.id == edge_id).first()


def create_graph_edge(db: Session, edge: schemas.GraphEdgeCreate):
    from app.models import GraphEdge
    existing = db.query(GraphEdge).filter(
        GraphEdge.source_id == edge.source_id,
        GraphEdge.target_id == edge.target_id,
        GraphEdge.edge_type == edge.edge_type
    ).first()
    if existing:
        return existing
    db_edge = GraphEdge(**edge.model_dump())
    db.add(db_edge)
    db.commit()
    db.refresh(db_edge)
    return db_edge


def delete_graph_edge(db: Session, edge_id: int):
    from app.models import GraphEdge
    db_edge = get_graph_edge(db, edge_id)
    if db_edge:
        db.delete(db_edge)
        db.commit()
    return db_edge


def get_graph_data(db: Session, project_id: int) -> schemas.GraphData:
    nodes = get_graph_nodes_by_project(db, project_id)
    edges = get_graph_edges_by_project(db, project_id)
    return schemas.GraphData(nodes=nodes, edges=edges)


def get_diff_relations_by_project(db: Session, project_id: int, relation_type: Optional[str] = None):
    from app.models import DiffRelation
    query = db.query(DiffRelation).filter(DiffRelation.project_id == project_id)
    if relation_type:
        query = query.filter(DiffRelation.relation_type == relation_type)
    return query.all()


def get_diff_relations_by_diff(db: Session, diff_id: int):
    from app.models import DiffRelation
    return db.query(DiffRelation).filter(
        (DiffRelation.source_diff_id == diff_id) | (DiffRelation.target_diff_id == diff_id)
    ).all()


def create_diff_relation(db: Session, relation: schemas.DiffRelationCreate):
    from app.models import DiffRelation
    existing = db.query(DiffRelation).filter(
        DiffRelation.source_diff_id == relation.source_diff_id,
        DiffRelation.target_diff_id == relation.target_diff_id,
        DiffRelation.relation_type == relation.relation_type
    ).first()
    if existing:
        return existing
    db_relation = DiffRelation(**relation.model_dump())
    db.add(db_relation)
    db.commit()
    db.refresh(db_relation)
    return db_relation


def delete_diff_relation(db: Session, relation_id: int):
    from app.models import DiffRelation
    db_relation = db.query(DiffRelation).filter(DiffRelation.id == relation_id).first()
    if db_relation:
        db.delete(db_relation)
        db.commit()
    return db_relation


def get_version_lineages_by_project(db: Session, project_id: int):
    from app.models import VersionLineage
    return db.query(VersionLineage).filter(VersionLineage.project_id == project_id).all()


def get_version_lineages_by_version(db: Session, version_id: int):
    from app.models import VersionLineage
    return db.query(VersionLineage).filter(
        (VersionLineage.parent_version_id == version_id) | (VersionLineage.child_version_id == version_id)
    ).all()


def create_version_lineage(db: Session, lineage: schemas.VersionLineageCreate):
    from app.models import VersionLineage
    existing = db.query(VersionLineage).filter(
        VersionLineage.parent_version_id == lineage.parent_version_id,
        VersionLineage.child_version_id == lineage.child_version_id
    ).first()
    if existing:
        return existing
    db_lineage = VersionLineage(**lineage.model_dump())
    db.add(db_lineage)
    db.commit()
    db.refresh(db_lineage)
    return db_lineage


def delete_version_lineage(db: Session, lineage_id: int):
    from app.models import VersionLineage
    db_lineage = db.query(VersionLineage).filter(VersionLineage.id == lineage_id).first()
    if db_lineage:
        db.delete(db_lineage)
        db.commit()
    return db_lineage


def get_transmission_reports_by_project(db: Session, project_id: int, report_type: Optional[str] = None):
    from app.models import TransmissionReport
    query = db.query(TransmissionReport).filter(TransmissionReport.project_id == project_id)
    if report_type:
        query = query.filter(TransmissionReport.report_type == report_type)
    return query.order_by(TransmissionReport.created_at.desc()).all()


def get_transmission_report(db: Session, report_id: int):
    from app.models import TransmissionReport
    return db.query(TransmissionReport).filter(TransmissionReport.id == report_id).first()


def create_transmission_report(db: Session, report: schemas.TransmissionReportCreate):
    from app.models import TransmissionReport
    db_report = TransmissionReport(**report.model_dump())
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def delete_transmission_report(db: Session, report_id: int):
    from app.models import TransmissionReport
    db_report = get_transmission_report(db, report_id)
    if db_report:
        db.delete(db_report)
        db.commit()
    return db_report


def get_diffs_by_text_pattern(db: Session, project_id: int, text_pattern: str):
    from app.models import Diff
    return db.query(Diff).filter(
        Diff.project_id == project_id,
        Diff.text.like(f"%{text_pattern}%")
    ).all()


def build_graph_from_existing_data(db: Session, project_id: int) -> schemas.GraphData:
    from app.models import Version, Passage, Diff, CollationProposal, LiteratureCitation, CollationNote
    from app.models import GraphNode, GraphEdge

    versions = get_versions_by_project(db, project_id)
    diffs = get_diffs_by_project(db, project_id)
    proposals = db.query(CollationProposal).join(Diff).filter(Diff.project_id == project_id).all()
    citations = db.query(LiteratureCitation).join(CollationProposal).join(Diff).filter(Diff.project_id == project_id).all()

    node_map = {}

    for v in versions:
        node_data = schemas.GraphNodeCreate(
            project_id=project_id,
            node_type="version",
            ref_id=v.id,
            label=v.name,
            description=f"版本: {v.name}, 来源: {v.source or '未知'}"
        )
        node = create_graph_node(db, node_data)
        node_map[f"version_{v.id}"] = node

    volume_set = set()
    passages_all = db.query(Passage).join(Version).filter(Version.project_id == project_id).all()
    for p in passages_all:
        vol_key = f"volume_{p.version_id}_{p.volume_no}"
        if vol_key not in node_map:
            v_name = node_map[f"version_{p.version_id}"].label if f"version_{p.version_id}" in node_map else ""
            node_data = schemas.GraphNodeCreate(
                project_id=project_id,
                node_type="volume",
                ref_id=p.volume_no,
                label=f"第{p.volume_no}卷",
                description=f"版本: {v_name}, 第{p.volume_no}卷"
            )
            node = create_graph_node(db, node_data)
            node_map[vol_key] = node

    for d in diffs:
        diff_key = f"diff_{d.id}"
        if diff_key not in node_map:
            node_data = schemas.GraphNodeCreate(
                project_id=project_id,
                node_type="diff",
                ref_id=d.id,
                label=f"异文-{d.id}",
                description=f"类型: {d.diff_type}, 文本: {d.text or ''}, 状态: {d.status}"
            )
            node = create_graph_node(db, node_data)
            node_map[diff_key] = node

    for p in proposals:
        prop_key = f"proposal_{p.id}"
        if prop_key not in node_map:
            node_data = schemas.GraphNodeCreate(
                project_id=project_id,
                node_type="proposal",
                ref_id=p.id,
                label=p.title,
                description=f"提案: {p.title}, 作者: {p.author}, 状态: {'已采纳' if p.is_accepted else '待审'}"
            )
            node = create_graph_node(db, node_data)
            node_map[prop_key] = node

    for c in citations:
        cite_key = f"citation_{c.id}"
        if cite_key not in node_map:
            node_data = schemas.GraphNodeCreate(
                project_id=project_id,
                node_type="citation",
                ref_id=c.id,
                label=c.title,
                description=f"文献: {c.title}, 作者: {c.author or '未知'}"
            )
            node = create_graph_node(db, node_data)
            node_map[cite_key] = node

    for d in diffs:
        diff_node = node_map.get(f"diff_{d.id}")
        version_node = node_map.get(f"version_{d.version_id}")
        if diff_node and version_node:
            edge_data = schemas.GraphEdgeCreate(
                project_id=project_id,
                source_id=diff_node.id,
                target_id=version_node.id,
                edge_type="appears_in",
                weight=1
            )
            create_graph_edge(db, edge_data)

    for d in diffs:
        diff_node = node_map.get(f"diff_{d.id}")
        passage = get_passage(db, d.passage_id)
        if diff_node and passage:
            vol_key = f"volume_{d.version_id}_{passage.volume_no}"
            vol_node = node_map.get(vol_key)
            if vol_node:
                edge_data = schemas.GraphEdgeCreate(
                    project_id=project_id,
                    source_id=diff_node.id,
                    target_id=vol_node.id,
                    edge_type="located_in",
                    weight=1
                )
                create_graph_edge(db, edge_data)

    for p in proposals:
        prop_node = node_map.get(f"proposal_{p.id}")
        diff_node = node_map.get(f"diff_{p.diff_id}")
        if prop_node and diff_node:
            edge_data = schemas.GraphEdgeCreate(
                project_id=project_id,
                source_id=diff_node.id,
                target_id=prop_node.id,
                edge_type="has_proposal",
                weight=1
            )
            create_graph_edge(db, edge_data)

    for c in citations:
        cite_node = node_map.get(f"citation_{c.id}")
        prop_node = node_map.get(f"proposal_{c.proposal_id}")
        if cite_node and prop_node:
            edge_data = schemas.GraphEdgeCreate(
                project_id=project_id,
                source_id=prop_node.id,
                target_id=cite_node.id,
                edge_type="cites_literature",
                weight=1
            )
            create_graph_edge(db, edge_data)

    return get_graph_data(db, project_id)


def get_diff_graph_detail(db: Session, diff_id: int) -> schemas.DiffGraphDetail:
    from app.models import Diff, Version, CollationProposal, LiteratureCitation, CollationNote, DiffRelation

    diff = get_diff(db, diff_id)
    if not diff:
        return None

    version = get_version(db, diff.version_id)
    passage = get_passage(db, diff.passage_id)

    proposals = get_proposals_by_diff(db, diff_id)
    proposal_dicts = []
    citation_dicts = []
    for p in proposals:
        proposal_dicts.append({
            "id": p.id,
            "title": p.title,
            "author": p.author,
            "proposed_text": p.proposed_text,
            "is_accepted": p.is_accepted,
            "created_at": p.created_at
        })
        citations = get_citations_by_proposal(db, p.id)
        for c in citations:
            citation_dicts.append({
                "id": c.id,
                "proposal_id": p.id,
                "title": c.title,
                "author": c.author,
                "publication": c.publication,
                "quote_text": c.quote_text
            })

    diff_relations = get_diff_relations_by_diff(db, diff_id)
    related_diffs = []
    for rel in diff_relations:
        other_diff_id = rel.target_diff_id if rel.source_diff_id == diff_id else rel.source_diff_id
        other_diff = get_diff(db, other_diff_id)
        if other_diff:
            other_version = get_version(db, other_diff.version_id)
            related_diffs.append({
                "id": other_diff_id,
                "text": other_diff.text,
                "diff_type": other_diff.diff_type,
                "relation_type": rel.relation_type,
                "confidence": rel.confidence,
                "version_name": other_version.name if other_version else "未知"
            })

    notes = get_collation_notes_by_diff(db, diff_id)
    resolution_history = []
    for note in notes:
        resolution_history.append({
            "id": note.id,
            "author": note.author,
            "content": note.content,
            "evidence": note.evidence,
            "is_final": note.is_final,
            "created_at": note.created_at
        })

    versions_list = []
    if version:
        versions_list.append({
            "id": version.id,
            "name": version.name,
            "source": version.source,
            "year": version.year,
            "volume_no": passage.volume_no if passage else None,
            "paragraph_no": passage.paragraph_no if passage else None
        })

    return schemas.DiffGraphDetail(
        diff_id=diff.id,
        diff_text=diff.text or "",
        diff_type=diff.diff_type,
        status=diff.status,
        versions=versions_list,
        proposals=proposal_dicts,
        citations=citation_dicts,
        related_diffs=related_diffs,
        resolution_history=resolution_history
    )


def get_diff_distribution_by_versions(db: Session, project_id: int, diff_text: Optional[str] = None) -> List[schemas.DiffDistribution]:
    from app.models import Diff, Version

    versions = get_versions_by_project(db, project_id)
    result = []

    for v in versions:
        query = db.query(Diff).filter(
            Diff.project_id == project_id,
            Diff.version_id == v.id
        )
        if diff_text:
            query = query.filter(Diff.text.like(f"%{diff_text}%"))
        diffs = query.all()
        result.append(schemas.DiffDistribution(
            version_id=v.id,
            version_name=v.name,
            diff_count=len(diffs),
            diff_ids=[d.id for d in diffs]
        ))

    return result


def update_version(db: Session, version_id: int, version_update: schemas.VersionUpdate):
    from app.models import Version
    db_version = get_version(db, version_id)
    if db_version:
        update_data = version_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_version, key, value)
        db.commit()
        db.refresh(db_version)
    return db_version


def get_controversy_analyses_by_project(db: Session, project_id: int, analysis_type: Optional[str] = None):
    from app.models import ControversyAnalysis
    query = db.query(ControversyAnalysis).filter(ControversyAnalysis.project_id == project_id)
    if analysis_type:
        query = query.filter(ControversyAnalysis.analysis_type == analysis_type)
    return query.order_by(ControversyAnalysis.created_at.desc()).all()


def get_controversy_analysis(db: Session, analysis_id: int):
    from app.models import ControversyAnalysis
    return db.query(ControversyAnalysis).filter(ControversyAnalysis.id == analysis_id).first()


def create_controversy_analysis(db: Session, analysis: schemas.ControversyAnalysisCreate):
    from app.models import ControversyAnalysis
    db_analysis = ControversyAnalysis(**analysis.model_dump())
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    return db_analysis


def update_controversy_analysis(db: Session, analysis_id: int, **kwargs):
    from app.models import ControversyAnalysis
    db_analysis = get_controversy_analysis(db, analysis_id)
    if db_analysis:
        for key, value in kwargs.items():
            setattr(db_analysis, key, value)
        db.commit()
        db.refresh(db_analysis)
    return db_analysis


def delete_controversy_analysis(db: Session, analysis_id: int):
    from app.models import ControversyAnalysis
    db_analysis = get_controversy_analysis(db, analysis_id)
    if db_analysis:
        db.delete(db_analysis)
        db.commit()
    return db_analysis


def create_controversy_evidence(db: Session, evidence: schemas.ControversyEvidenceCreate):
    from app.models import ControversyEvidence
    db_evidence = ControversyEvidence(**evidence.model_dump())
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    return db_evidence


def get_evidences_by_controversy_analysis(db: Session, analysis_id: int):
    from app.models import ControversyEvidence
    return db.query(ControversyEvidence).filter(
        ControversyEvidence.controversy_analysis_id == analysis_id
    ).all()


def get_temporal_snapshots_by_project(db: Session, project_id: int, diff_id: Optional[int] = None):
    from app.models import TemporalEvolutionSnapshot
    query = db.query(TemporalEvolutionSnapshot).filter(TemporalEvolutionSnapshot.project_id == project_id)
    if diff_id:
        query = query.filter(TemporalEvolutionSnapshot.diff_id == diff_id)
    return query.order_by(TemporalEvolutionSnapshot.year_start).all()


def create_temporal_snapshot(db: Session, snapshot: schemas.TemporalEvolutionSnapshotCreate):
    from app.models import TemporalEvolutionSnapshot
    db_snapshot = TemporalEvolutionSnapshot(**snapshot.model_dump())
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    return db_snapshot


def delete_temporal_snapshots_by_project(db: Session, project_id: int):
    from app.models import TemporalEvolutionSnapshot
    db.query(TemporalEvolutionSnapshot).filter(
        TemporalEvolutionSnapshot.project_id == project_id
    ).delete()
    db.commit()


def get_controversy_reports_by_project(db: Session, project_id: int, report_type: Optional[str] = None):
    from app.models import ControversyReport
    query = db.query(ControversyReport).filter(ControversyReport.project_id == project_id)
    if report_type:
        query = query.filter(ControversyReport.report_type == report_type)
    return query.order_by(ControversyReport.created_at.desc()).all()


def get_controversy_report(db: Session, report_id: int):
    from app.models import ControversyReport
    return db.query(ControversyReport).filter(ControversyReport.id == report_id).first()


def create_controversy_report(db: Session, report: schemas.ControversyReportCreate):
    from app.models import ControversyReport
    db_report = ControversyReport(**report.model_dump())
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def delete_controversy_report(db: Session, report_id: int):
    from app.models import ControversyReport
    db_report = get_controversy_report(db, report_id)
    if db_report:
        db.delete(db_report)
        db.commit()
    return db_report


def get_versions_with_metadata(db: Session, project_id: int):
    from app.models import Version
    return db.query(Version).filter(Version.project_id == project_id).all()


def get_diffs_with_filters(
    db: Session,
    project_id: int,
    time_period_start: Optional[str] = None,
    time_period_end: Optional[str] = None,
    region_filter: Optional[str] = None,
    diff_type_filter: Optional[str] = None,
    version_system_filter: Optional[str] = None
):
    from app.models import Diff, Version, Passage
    query = db.query(Diff).join(Version).join(Passage).filter(
        Diff.project_id == project_id
    )

    if diff_type_filter:
        query = query.filter(Diff.diff_type == diff_type_filter)

    if region_filter:
        query = query.filter(Version.region == region_filter)

    if version_system_filter:
        query = query.filter(Version.version_system == version_system_filter)

    return query.all()


def get_controversy_evidences_by_position(db: Session, analysis_id: int, position: str):
    from app.models import ControversyEvidence
    return db.query(ControversyEvidence).filter(
        ControversyEvidence.controversy_analysis_id == analysis_id,
        ControversyEvidence.position == position
    ).order_by(ControversyEvidence.strength.desc()).all()
