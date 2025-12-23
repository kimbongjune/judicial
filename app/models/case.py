"""
판례 (prec) 모델 정의
"""
from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Text, Date, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Case(Base):
    """
    판례 테이블
    법제처 OpenAPI의 판례 목록/상세 데이터 저장
    """
    __tablename__ = "cases"
    
    # 기본 키
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 판례 식별 정보
    case_serial_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="법제처 판례 고유 일련번호")
    case_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="사건번호 (예: 2023다12345)")
    case_type_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="사건종류코드")
    case_type_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="사건종류명 (민사, 형사 등)")
    
    # 법원 및 재판 정보
    court_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="법원명 (대법원, 서울고등법원 등)")
    court_type_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="법원종류코드")
    judgment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="선고/결정/명령 구분")
    
    # 날짜 정보
    judgment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True, comment="선고일자")
    
    # 판례 내용
    case_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="판례 제목/사건명")
    decision_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="판결유형 (판결, 결정 등)")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="판시사항 요약")
    gist: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="판결요지")
    reference_provisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조조문 목록")
    reference_cases: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조판례 목록")
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="판례 전문")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="데이터 생성 시간")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="데이터 수정 시간")
    
    # 복합 인덱스
    __table_args__ = (
        Index("ix_cases_court_name_judgment_date", "court_name", "judgment_date"),
        Index("ix_cases_case_type_name_judgment_date", "case_type_name", "judgment_date"),
    )
    
    def __repr__(self) -> str:
        return f"<Case(id={self.id}, case_number='{self.case_number}', case_name='{self.case_name[:30]}...')>"
    
    @property
    def search_text(self) -> str:
        """유사도 검색용 텍스트 생성"""
        parts = []
        if self.case_name:
            parts.append(self.case_name)
        if self.summary:
            parts.append(self.summary)
        if self.gist:
            parts.append(self.gist)
        return " ".join(parts)
