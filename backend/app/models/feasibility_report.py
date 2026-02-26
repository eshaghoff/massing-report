from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.database import Base


class FeasibilityReport(Base):
    __tablename__ = "feasibility_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bbl = Column(String(10), ForeignKey("lots.bbl"))
    assemblage_bbls = Column(ARRAY(String(10)), nullable=True)
    scenarios = Column(JSONB, default={})
    report_pdf_path = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
