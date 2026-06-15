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
