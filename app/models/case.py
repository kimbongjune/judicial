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
    판례일련번호: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="법제처 판례 고유 일련번호")
    사건번호: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="사건번호 (예: 2023다12345)")
    사건종류코드: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="사건종류코드")
    사건종류명: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="사건종류명 (민사, 형사 등)")
    
    # 법원 및 재판 정보
    법원명: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="법원명 (대법원, 서울고등법원 등)")
    법원종류코드: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="법원종류코드")
    선고: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="선고/결정/명령 구분")
    
    # 날짜 정보
    선고일자: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True, comment="선고일자")
    
    # 판례 내용
    사건명: Mapped[str] = mapped_column(String(500), nullable=False, comment="판례 제목/사건명")
    판결유형: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="판결유형 (판결, 결정 등)")
    판시사항: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="판시사항 요약")
    판결요지: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="판결요지")
    참조조문: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조조문 목록")
    참조판례: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조판례 목록")
    판례내용: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="판례 전문")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="데이터 생성 시간")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="데이터 수정 시간")
    
    # 복합 인덱스
    __table_args__ = (
        Index("ix_cases_법원명_선고일자", "법원명", "선고일자"),
        Index("ix_cases_사건종류명_선고일자", "사건종류명", "선고일자"),
    )
    
    def __repr__(self) -> str:
        return f"<Case(id={self.id}, 사건번호='{self.사건번호}', 사건명='{self.사건명[:30]}...')>"
    
    @property
    def search_text(self) -> str:
        """유사도 검색용 텍스트 생성"""
        parts = []
        if self.사건명:
            parts.append(self.사건명)
        if self.판시사항:
            parts.append(self.판시사항)
        if self.판결요지:
            parts.append(self.판결요지)
        return " ".join(parts)
