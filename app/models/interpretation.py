"""
법령해석례 (expc) 모델 정의
"""
from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Text, Date, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Interpretation(Base):
    """
    법령해석례 테이블
    법제처 법령해석 데이터 저장
    """
    __tablename__ = "interpretations"
    
    # 기본 키
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 해석례 식별 정보
    interpretation_serial_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="법령해석례 일련번호")
    agenda_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="안건번호")
    
    # 분류 정보
    field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="분야")
    law_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="법령구분명")
    
    # 날짜 정보
    reply_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True, comment="회신일자")
    
    # 해석례 내용
    agenda_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="안건명")
    question_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="질의요지")
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="회답")
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="이유")
    reference_provisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조조문")
    reference_cases: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조판례")
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="비고")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_interpretations_field_date", "field", "reply_date"),
    )
    
    def __repr__(self) -> str:
        return f"<Interpretation(id={self.id}, agenda_number='{self.agenda_number}')>"
    
    @property
    def search_text(self) -> str:
        """유사도 검색용 텍스트"""
        parts = []
        if self.agenda_name:
            parts.append(self.agenda_name)
        if self.question_summary:
            parts.append(self.question_summary)
        if self.answer:
            parts.append(self.answer)
        return " ".join(parts)
