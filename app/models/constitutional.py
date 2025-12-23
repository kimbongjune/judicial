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
    법제처 OpenAPI의 헌법재판소 결정례 데이터 저장
    """
    __tablename__ = "constitutional_decisions"
    
    # 기본 키
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 결정례 식별 정보
    decision_serial_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="법제처 결정례 고유 일련번호")
    case_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="사건번호 (예: 2023헌바123)")
    case_type_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="사건종류코드")
    case_type_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, comment="사건종류명 (헌마, 헌바, 헌가 등)")
    
    # 날짜 정보
    decision_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True, comment="선고일자")
    
    # 결정례 내용
    case_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="결정례 제목/사건명")
    decision_result: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="결정 결과 (위헌, 합헌, 각하 등)")
    ruling: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="주문 내용")
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="결정 이유")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="결정요지 요약")
    reference_provisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조조문 목록")
    reference_cases: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조판례 목록")
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="결정문 전문")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="데이터 생성 시간")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="데이터 수정 시간")
    
    # 복합 인덱스
    __table_args__ = (
        Index("ix_constitutional_decisions_case_type_name_decision_date", "case_type_name", "decision_date"),
        Index("ix_constitutional_decisions_decision_result", "decision_result"),
    )
    
    def __repr__(self) -> str:
        return f"<ConstitutionalDecision(id={self.id}, case_number='{self.case_number}', case_name='{self.case_name[:30]}...')>"
    
    @property
    def search_text(self) -> str:
        """유사도 검색용 텍스트 생성"""
        parts = []
        if self.case_name:
            parts.append(self.case_name)
        if self.summary:
            parts.append(self.summary)
        if self.ruling:
            parts.append(self.ruling)
        return " ".join(parts)
