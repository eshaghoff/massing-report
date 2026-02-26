from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Lot(Base):
    __tablename__ = "lots"

    bbl = Column(String(10), primary_key=True)
    borough = Column(Integer)
    block = Column(Integer)
    lot = Column(Integer)
    address = Column(Text)
    geom = Column(Geometry("Polygon", srid=4326), nullable=True)
    pluto_data = Column(JSONB, default={})
    zoning_data = Column(JSONB, default={})
    last_updated = Column(DateTime, default=datetime.utcnow)
