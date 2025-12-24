"""
북마크 모델 정의
사용자가 관심 있는 판례/헌재결정례/법령해석례를 저장
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Bookmark(Base):
    """
    북마크 테이블
    브라우저 세션별로 북마크 저장
    """
    __tablename__ = "bookmarks"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 세션 식별
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="브라우저 세션 ID")
    
    # 북마크 대상
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="엔티티 타입 (case, constitutional, interpretation)")
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="대상 엔티티의 ID")
    
    # 메타 정보 (표시용 캐시)
    entity_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="엔티티 제목 캐시")
    entity_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="사건번호 캐시")
    
    # 생성 시간
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="북마크 생성 시간")
    
    __table_args__ = (
        Index("ix_bookmarks_session_entity", "session_id", "entity_type", "entity_id", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<Bookmark(id={self.id}, entity_type='{self.entity_type}', entity_id={self.entity_id})>"
