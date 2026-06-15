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
