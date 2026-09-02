"""Prompt IDE models.

Templates and immutable versions are kept separate from ``PromptRecord`` so
existing generated-history data remains backwards compatible.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class PromptTemplate(Base):
    """A reusable prompt template with ``{{variable}}`` placeholders."""

    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    variables = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)
    current_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PromptVersion(Base):
    """Immutable snapshot of a prompt template."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_prompt_version_template_version"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(
        Integer,
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    variables = Column(JSON, nullable=False, default=list)
    change_note = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
