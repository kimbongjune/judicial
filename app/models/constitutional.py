"""
헌재결정례 (detc) 모델 정의
"""
from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Text, Date, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConstitutionalDecision(Base):
    """
    헌재결정례 테이블
    헌법재판소 결정례 데이터 저장
    """
    __tablename__ = "constitutional_decisions"
    
    # 기본 키
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 결정례 식별 정보
    decision_serial_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="결정례 일련번호")
    case_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="사건번호")
    case_type_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="사건종류코드")
    case_type_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="사건종류명")
    
    # 날짜 정보
    decision_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True, comment="선고일자")
    
    # 결정례 내용
    case_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="사건명")
    decision_result: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="결정결과")
    ruling: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="주문")
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="이유")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="결정요지")
    reference_provisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조조문")
    reference_cases: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조판례")
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="결정문 전문")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_constitutional_case_type_date", "case_type_name", "decision_date"),
    )
    
    def __repr__(self) -> str:
        return f"<ConstitutionalDecision(id={self.id}, case_number='{self.case_number}')>"
    
    @property
    def search_text(self) -> str:
        """유사도 검색용 텍스트"""
        parts = []
        if self.case_name:
            parts.append(self.case_name)
        if self.summary:
            parts.append(self.summary)
        return " ".join(parts)
