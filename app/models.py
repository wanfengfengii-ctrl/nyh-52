from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    book_title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    versions = relationship("Version", back_populates="project", cascade="all, delete-orphan")
    diffs = relationship("Diff", back_populates="project", cascade="all, delete-orphan")


class Version(Base):
    __tablename__ = "version"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    source = Column(Text, nullable=True)
    year = Column(String(50), nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_version_name"),)

    project = relationship("Project", back_populates="versions")
    passages = relationship("Passage", back_populates="version", cascade="all, delete-orphan")
    diffs = relationship("Diff", back_populates="version", cascade="all, delete-orphan")


class Passage(Base):
    __tablename__ = "passage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("version.id", ondelete="CASCADE"), nullable=False)
    volume_no = Column(Integer, nullable=False)
    paragraph_no = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (UniqueConstraint("version_id", "volume_no", "paragraph_no", name="uq_version_volume_paragraph"),)

    version = relationship("Version", back_populates="passages")
    diffs = relationship("Diff", back_populates="passage", cascade="all, delete-orphan")


class Diff(Base):
    __tablename__ = "diff"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    passage_id = Column(Integer, ForeignKey("passage.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(Integer, ForeignKey("version.id", ondelete="CASCADE"), nullable=False)
    diff_type = Column(String(20), nullable=False)
    position_start = Column(Integer, nullable=False)
    position_end = Column(Integer, nullable=False)
    text = Column(Text, nullable=True)
    reference_text = Column(Text, nullable=True)
    status = Column(String(20), default="pending")

    project = relationship("Project", back_populates="diffs")
    passage = relationship("Passage", back_populates="diffs")
    version = relationship("Version", back_populates="diffs")
    collation_notes = relationship("CollationNote", back_populates="diff", cascade="all, delete-orphan")
    proposals = relationship("CollationProposal", back_populates="diff", cascade="all, delete-orphan")
    discussions = relationship("DiscussionMessage", back_populates="diff", cascade="all, delete-orphan")


class CollationNote(Base):
    __tablename__ = "collation_note"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diff_id = Column(Integer, ForeignKey("diff.id", ondelete="CASCADE"), nullable=False)
    author = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)
    is_final = Column(Boolean, default=False)
    needs_review = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    diff = relationship("Diff", back_populates="collation_notes")


class CollationProposal(Base):
    __tablename__ = "collation_proposal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diff_id = Column(Integer, ForeignKey("diff.id", ondelete="CASCADE"), nullable=False)
    author = Column(String(255), nullable=False)
    title = Column(String(500), nullable=False)
    proposed_text = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    diff = relationship("Diff", back_populates="proposals")
    citations = relationship("LiteratureCitation", back_populates="proposal", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="proposal", cascade="all, delete-orphan")
    review_records = relationship("ReviewRecord", back_populates="proposal", cascade="all, delete-orphan")


class LiteratureCitation(Base):
    __tablename__ = "literature_citation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id = Column(Integer, ForeignKey("collation_proposal.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    author = Column(String(255), nullable=True)
    publication = Column(String(500), nullable=True)
    page_info = Column(String(255), nullable=True)
    quote_text = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    proposal = relationship("CollationProposal", back_populates="citations")


class Vote(Base):
    __tablename__ = "vote"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id = Column(Integer, ForeignKey("collation_proposal.id", ondelete="CASCADE"), nullable=False)
    voter = Column(String(255), nullable=False)
    vote_type = Column(String(20), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint("proposal_id", "voter", name="uq_proposal_voter"),)

    proposal = relationship("CollationProposal", back_populates="votes")


class DiscussionMessage(Base):
    __tablename__ = "discussion_message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diff_id = Column(Integer, ForeignKey("diff.id", ondelete="CASCADE"), nullable=False)
    author = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    reply_to_id = Column(Integer, ForeignKey("discussion_message.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    diff = relationship("Diff", back_populates="discussions")
    reply_to = relationship("DiscussionMessage", remote_side=[id])


class ReviewRecord(Base):
    __tablename__ = "review_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id = Column(Integer, ForeignKey("collation_proposal.id", ondelete="CASCADE"), nullable=False)
    reviewer = Column(String(255), nullable=False)
    review_result = Column(String(20), nullable=False)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    proposal = relationship("CollationProposal", back_populates="review_records")


class RecommendedText(Base):
    __tablename__ = "recommended_text"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    volume_no = Column(Integer, nullable=False)
    paragraph_no = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(20), default="draft")
    generated_by = Column(String(255), nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    base_version_id = Column(Integer, ForeignKey("version.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (UniqueConstraint("project_id", "volume_no", "paragraph_no", name="uq_project_volume_paragraph_recommended"),)

    project = relationship("Project")
    base_version = relationship("Version")
    evidences = relationship("RecommendedTextEvidence", back_populates="recommended_text", cascade="all, delete-orphan")


class RecommendedTextEvidence(Base):
    __tablename__ = "recommended_text_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommended_text_id = Column(Integer, ForeignKey("recommended_text.id", ondelete="CASCADE"), nullable=False)
    diff_id = Column(Integer, ForeignKey("diff.id", ondelete="SET NULL"), nullable=True)
    proposal_id = Column(Integer, ForeignKey("collation_proposal.id", ondelete="SET NULL"), nullable=True)
    evidence_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    source_version_name = Column(String(255), nullable=True)

    recommended_text = relationship("RecommendedText", back_populates="evidences")
