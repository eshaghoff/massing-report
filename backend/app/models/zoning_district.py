from __future__ import annotations

from sqlalchemy import Column, String, Float
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class ZoningDistrict(Base):
    __tablename__ = "zoning_districts"

    district_code = Column(String(10), primary_key=True)
    residential_far = Column(JSONB)
    commercial_far = Column(Float, nullable=True)
    cf_far = Column(Float, nullable=True)
    manufacturing_far = Column(Float, nullable=True)
    height_limits = Column(JSONB, default={})
    setback_rules = Column(JSONB, default={})
    yard_rules = Column(JSONB, default={})
    parking_rules = Column(JSONB, default={})
    permitted_uses = Column(JSONB, default={})
