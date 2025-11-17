# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
from datetime import datetime
from .db import Base

class QAResult(Base):
    __tablename__ = "qa_results"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    title = Column(String, nullable=True)
    findings = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Language(Base):
    __tablename__ = "languages"
    __table_args__ = (UniqueConstraint('locale_code', name='uix_locale_code'),)


    id = Column(Integer, primary_key=True, index=True)
    language_name = Column(String, nullable=False)
    locale_code = Column(String, nullable=False)