"""
검색 로그 모델 정의
검색 히스토리 및 통계 용도
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SearchLog(Base):
    """
    검색 로그 테이블
    사용자 검색 기록 저장 (통계 및 히스토리용)
    """
    __tablename__ = "search_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 검색 정보
    query: Mapped[str] = mapped_column(String(500), nullable=False, comment="검색어")
    search_type: Mapped[str] = mapped_column(String(50), nullable=False, default="keyword", comment="검색 타입 (keyword, semantic, similar)")
    
    # 결과 정보
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="검색 결과 수")
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="응답 시간 (ms)")
    
    # 필터 정보
    filters_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="적용된 필터 (JSON)")
    
    # 세션 정보
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="세션 ID")
    
    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, comment="검색 시간")
    
    __table_args__ = (
        Index("ix_search_logs_query", "query"),
        Index("ix_search_logs_type_date", "search_type", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<SearchLog(id={self.id}, query='{self.query[:30]}...', type='{self.search_type}')>"
