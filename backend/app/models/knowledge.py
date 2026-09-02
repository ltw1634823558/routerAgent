"""Knowledge pipeline persistence models.

The original ``knowledge_base`` table stores source documents.  These two
tables keep the derived chunks and asynchronous import jobs separate, so the
existing API remains backwards compatible.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.database import Base


class KnowledgeChunk(Base):
    """A searchable piece of a knowledge document."""

    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(
        Integer,
        ForeignKey("knowledge_base.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(500), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeImportJob(Base):
    """Persistent state for URL/crawler imports."""

    __tablename__ = "knowledge_import_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    source_type = Column(String(30), nullable=False, default="url")
    target = Column(String(1000), nullable=True)
    options = Column(JSON, nullable=True)
    total_items = Column(Integer, nullable=False, default=0)
    imported_items = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
