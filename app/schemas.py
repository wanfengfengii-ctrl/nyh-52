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


class VersionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    source: Optional[str] = None
    year: Optional[str] = Field(None, max_length=50)
    region: Optional[str] = Field(None, max_length=255)
    version_system: Optional[str] = Field(None, max_length=255)
    year_numeric: Optional[int] = None


class ControversyEvidenceBase(BaseModel):
    evidence_type: str = Field(..., max_length=20)
    position: str = Field(..., max_length=20)
    source: str = Field(..., max_length=500)
    content: str = Field(..., min_length=1)
    strength: int = 50
    author: Optional[str] = Field(None, max_length=255)


class ControversyEvidenceCreate(ControversyEvidenceBase):
    controversy_analysis_id: int


class ControversyEvidence(ControversyEvidenceBase):
    id: int
    controversy_analysis_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ControversyAnalysisBase(BaseModel):
    analysis_type: str = Field("controversy_heat", max_length=50)
    time_period_start: Optional[str] = Field(None, max_length=50)
    time_period_end: Optional[str] = Field(None, max_length=50)
    region_filter: Optional[str] = Field(None, max_length=255)
    diff_type_filter: Optional[str] = Field(None, max_length=50)
    version_system_filter: Optional[str] = Field(None, max_length=255)


class ControversyAnalysisCreate(ControversyAnalysisBase):
    project_id: int
    diff_id: Optional[int] = None
    created_by: Optional[str] = Field(None, max_length=255)


class ControversyAnalysis(ControversyAnalysisBase):
    id: int
    project_id: int
    diff_id: Optional[int] = None
    controversy_score: int = 0
    heat_level: str = "low"
    total_proposals: int = 0
    total_votes: int = 0
    total_discussions: int = 0
    vote_divergence: int = 0
    evidence_conflict_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime
    evidences: List[ControversyEvidence] = []

    class Config:
        from_attributes = True


class TemporalEvolutionSnapshotBase(BaseModel):
    period_label: str = Field(..., max_length=100)
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    region: Optional[str] = Field(None, max_length=255)


class TemporalEvolutionSnapshotCreate(TemporalEvolutionSnapshotBase):
    project_id: int
    diff_id: Optional[int] = None


class TemporalEvolutionSnapshot(TemporalEvolutionSnapshotBase):
    id: int
    project_id: int
    diff_id: Optional[int] = None
    version_count: int = 0
    diff_count: int = 0
    variant_texts: Optional[str] = None
    dominant_text: Optional[str] = Field(None, max_length=500)
    stability_score: int = 0
    change_rate: int = 0
    evidence_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ControversyReportBase(BaseModel):
    title: str = Field(..., max_length=500)
    report_type: str = Field("controversy_analysis", max_length=50)
    target_diff_id: Optional[int] = None
    time_period_start: Optional[str] = Field(None, max_length=50)
    time_period_end: Optional[str] = Field(None, max_length=50)
    region_filter: Optional[str] = Field(None, max_length=255)
    diff_type_filter: Optional[str] = Field(None, max_length=50)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = None
    analysis_method: Optional[str] = Field(None, max_length=100)
    findings_count: int = 0
    high_controversy_count: int = 0
    stable_inheritance_count: int = 0
    late_addition_count: int = 0
    unresolved_count: int = 0
    created_by: Optional[str] = Field(None, max_length=255)


class ControversyReportCreate(ControversyReportBase):
    project_id: int


class ControversyReport(ControversyReportBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ControversyHeatItem(BaseModel):
    diff_id: int
    diff_text: str
    diff_type: str
    volume_no: int
    paragraph_no: int
    controversy_score: int
    heat_level: str
    total_proposals: int
    total_votes: int
    vote_divergence: int
    evidence_conflict_count: int
    version_name: str
    status: str


class TemporalEvolutionDataPoint(BaseModel):
    period_label: str
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    version_count: int
    diff_count: int
    variant_texts: List[str] = []
    dominant_text: str
    stability_score: int
    change_rate: int
    region: Optional[str] = None


class RegionalDistributionItem(BaseModel):
    region: str
    version_count: int
    diff_count: int
    unique_variants: List[str] = []
    dominant_variant: str
    controversy_score: int


class VersionSystemDistributionItem(BaseModel):
    version_system: str
    version_count: int
    diff_count: int
    unique_variants: List[str] = []
    dominant_variant: str
    stability_score: int


class ControversyAnalysisResult(BaseModel):
    project_id: int
    analysis_type: str
    total_diffs_analyzed: int
    high_controversy_count: int
    medium_controversy_count: int
    low_controversy_count: int
    heat_items: List[ControversyHeatItem] = []
    temporal_evolution: List[TemporalEvolutionDataPoint] = []
    regional_distribution: List[RegionalDistributionItem] = []
    version_system_distribution: List[VersionSystemDistributionItem] = []
    time_period_start: Optional[str] = None
    time_period_end: Optional[str] = None
    region_filter: Optional[str] = None
    diff_type_filter: Optional[str] = None
    version_system_filter: Optional[str] = None
    supporting_evidences: List[ControversyEvidence] = []
    opposing_evidences: List[ControversyEvidence] = []
    key_findings: List[str] = []
    analysis_method: str = "multi_factor_controversy_analysis"


class DiffEvolutionPathItem(BaseModel):
    diff_id: int
    diff_text: str
    version_name: str
    version_year: Optional[str] = None
    version_region: Optional[str] = None
    version_system: Optional[str] = None
    year_numeric: Optional[int] = None
    diff_type: str
    status: str
    period_label: str


class DiffControversyDetail(BaseModel):
    diff_id: int
    diff_text: str
    diff_type: str
    status: str
    volume_no: int
    paragraph_no: int
    version_name: str
    controversy_score: int
    heat_level: str
    total_proposals: int
    total_votes: int
    total_discussions: int
    vote_divergence: int
    evidence_conflict_count: int
    agree_count: int
    disagree_count: int
    abstain_count: int
    proposals: List[dict] = []
    discussions: List[dict] = []
    supporting_evidences: List[dict] = []
    opposing_evidences: List[dict] = []
    evolution_path: List[DiffEvolutionPathItem] = []
    temporal_trend: List[dict] = []


class ControversyTimelineItem(BaseModel):
    period_label: str
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    diff_count: int
    new_variants: int
    resolved_count: int
    controversy_score: int
    discussion_count: int
    key_events: List[str] = []
