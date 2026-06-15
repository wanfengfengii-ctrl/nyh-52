from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    book_title: str = Field(..., min_length=1, max_length=255)


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VersionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source: Optional[str] = None
    year: Optional[str] = Field(None, max_length=50)


class VersionCreate(VersionBase):
    project_id: int


class Version(VersionBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True


class PassageBase(BaseModel):
    volume_no: int = Field(..., ge=1)
    paragraph_no: int = Field(..., ge=1)
    content: str = Field(..., min_length=1)


class PassageCreate(PassageBase):
    version_id: int


class PassageUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class Passage(PassageBase):
    id: int
    version_id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class DiffBase(BaseModel):
    diff_type: str
    position_start: int
    position_end: int
    text: Optional[str] = None
    reference_text: Optional[str] = None
    status: str = "pending"


class DiffCreate(DiffBase):
    project_id: int
    passage_id: int
    version_id: int


class Diff(DiffBase):
    id: int
    project_id: int
    passage_id: int
    version_id: int

    class Config:
        from_attributes = True


class CollationNoteBase(BaseModel):
    author: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    evidence: Optional[str] = None
    is_final: bool = False
    needs_review: bool = False


class CollationNoteCreate(CollationNoteBase):
    diff_id: int


class CollationNote(CollationNoteBase):
    id: int
    diff_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DiffWithNotes(Diff):
    collation_notes: List[CollationNote] = []


class ProjectStats(BaseModel):
    total_versions: int = 0
    total_passages: int = 0
    total_diffs: int = 0
    pending_diffs: int = 0
    reviewed_diffs: int = 0
    finalized_diffs: int = 0
    progress_percent: float = 0.0
    recommended_paragraphs: int = 0
    reviewed_recommended: int = 0


class LiteratureCitationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=255)
    publication: Optional[str] = Field(None, max_length=500)
    page_info: Optional[str] = Field(None, max_length=255)
    quote_text: Optional[str] = None
    note: Optional[str] = None


class LiteratureCitationCreate(LiteratureCitationBase):
    proposal_id: int


class LiteratureCitation(LiteratureCitationBase):
    id: int
    proposal_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VoteBase(BaseModel):
    voter: str = Field(..., min_length=1, max_length=255)
    vote_type: str = Field(..., min_length=1, max_length=20)
    comment: Optional[str] = None


class VoteCreate(VoteBase):
    proposal_id: int


class Vote(VoteBase):
    id: int
    proposal_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewRecordBase(BaseModel):
    reviewer: str = Field(..., min_length=1, max_length=255)
    review_result: str = Field(..., min_length=1, max_length=20)
    review_comment: Optional[str] = None


class ReviewRecordCreate(ReviewRecordBase):
    proposal_id: int


class ReviewRecord(ReviewRecordBase):
    id: int
    proposal_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CollationProposalBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    proposed_text: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1, max_length=255)


class CollationProposalCreate(CollationProposalBase):
    diff_id: int


class CollationProposalUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    proposed_text: Optional[str] = None
    rationale: Optional[str] = None


class CollationProposal(CollationProposalBase):
    id: int
    diff_id: int
    is_accepted: bool
    created_at: datetime
    updated_at: datetime
    citations: List[LiteratureCitation] = []
    votes: List[Vote] = []
    review_records: List[ReviewRecord] = []

    class Config:
        from_attributes = True


class DiscussionMessageBase(BaseModel):
    author: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    reply_to_id: Optional[int] = None


class DiscussionMessageCreate(DiscussionMessageBase):
    diff_id: int


class DiscussionMessage(DiscussionMessageBase):
    id: int
    diff_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendedTextEvidenceBase(BaseModel):
    evidence_type: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    diff_id: Optional[int] = None
    proposal_id: Optional[int] = None
    source_version_name: Optional[str] = Field(None, max_length=255)


class RecommendedTextEvidenceCreate(RecommendedTextEvidenceBase):
    recommended_text_id: int


class RecommendedTextEvidence(RecommendedTextEvidenceBase):
    id: int
    recommended_text_id: int

    class Config:
        from_attributes = True


class RecommendedTextBase(BaseModel):
    content: str = Field(..., min_length=1)
    status: str = "draft"
    base_version_id: Optional[int] = None
    generated_by: Optional[str] = Field(None, max_length=255)


class RecommendedTextCreate(RecommendedTextBase):
    project_id: int
    volume_no: int
    paragraph_no: int


class RecommendedTextUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None
    reviewed_by: Optional[str] = None


class RecommendedText(RecommendedTextBase):
    id: int
    project_id: int
    volume_no: int
    paragraph_no: int
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    evidences: List[RecommendedTextEvidence] = []

    class Config:
        from_attributes = True


class VolumeProgress(BaseModel):
    volume_no: int
    total_paragraphs: int = 0
    recommended_count: int = 0
    reviewed_count: int = 0
    progress_percent: float = 0.0


class ProposalVoteSummary(BaseModel):
    proposal_id: int
    agree_count: int = 0
    disagree_count: int = 0
    abstain_count: int = 0
    total_votes: int = 0


class GraphNodeBase(BaseModel):
    node_type: str = Field(..., min_length=1, max_length=50)
    ref_id: Optional[int] = None
    label: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    properties: Optional[str] = None


class GraphNodeCreate(GraphNodeBase):
    project_id: int


class GraphNode(GraphNodeBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class GraphEdgeBase(BaseModel):
    edge_type: str = Field(..., min_length=1, max_length=50)
    weight: int = 1
    properties: Optional[str] = None


class GraphEdgeCreate(GraphEdgeBase):
    project_id: int
    source_id: int
    target_id: int


class GraphEdge(GraphEdgeBase):
    id: int
    project_id: int
    source_id: int
    target_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class GraphData(BaseModel):
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []


class DiffRelationBase(BaseModel):
    relation_type: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    confidence: int = 50
    created_by: Optional[str] = Field(None, max_length=255)


class DiffRelationCreate(DiffRelationBase):
    project_id: int
    source_diff_id: int
    target_diff_id: int


class DiffRelation(DiffRelationBase):
    id: int
    project_id: int
    source_diff_id: int
    target_diff_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VersionLineageBase(BaseModel):
    relation_type: str = Field("direct_copy", max_length=50)
    description: Optional[str] = None
    confidence: int = 50
    evidence: Optional[str] = None
    created_by: Optional[str] = Field(None, max_length=255)


class VersionLineageCreate(VersionLineageBase):
    project_id: int
    parent_version_id: int
    child_version_id: int


class VersionLineage(VersionLineageBase):
    id: int
    project_id: int
    parent_version_id: int
    child_version_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TransmissionReportBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    report_type: str = Field("diff_transmission", max_length=50)
    target_diff_id: Optional[int] = None
    content: str = Field(..., min_length=1)
    summary: Optional[str] = None
    analysis_method: Optional[str] = Field(None, max_length=100)
    findings_count: int = 0
    created_by: Optional[str] = Field(None, max_length=255)


class TransmissionReportCreate(TransmissionReportBase):
    project_id: int


class TransmissionReport(TransmissionReportBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TransmissionPath(BaseModel):
    path: List[int] = []
    version_names: List[str] = []
    total_weight: int = 0
    path_type: str = "unknown"
    evidence_count: int = 0


class DiffDistribution(BaseModel):
    version_id: int
    version_name: str
    diff_count: int
    diff_ids: List[int] = []


class DiffGraphDetail(BaseModel):
    diff_id: int
    diff_text: str
    diff_type: str
    status: str
    versions: List[dict] = []
    proposals: List[dict] = []
    citations: List[dict] = []
    related_diffs: List[dict] = []
    resolution_history: List[dict] = []


class TransmissionAnalysisResult(BaseModel):
    target_diff_id: int
    analysis_method: str
    total_paths: int = 0
    transmission_paths: List[TransmissionPath] = []
    likely_cause: str = "unknown"
    confidence: int = 0
    key_findings: List[str] = []
