"""
법령 관련 모델 정의
- Law: 법령 기본 정보
- LawArticle: 법령 조문
- LawTerm: 법령 용어
- LawHistory: 법령 연혁
"""
from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Text, Date, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Law(Base):
    """
    법령 테이블
    법률, 대통령령, 부령 등 법령 기본 정보
    """
    __tablename__ = "laws"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 법령 식별 정보
    law_serial_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="법령 일련번호")
    law_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True, comment="법령 ID")
    law_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True, comment="법령명")
    law_name_korean: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="법령명(한글)")
    law_name_abbreviated: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="약칭")
    
    # 분류
    law_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True, comment="법령구분 (법률/대통령령/부령)")
    ministry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="소관부처")
    
    # 상태
    enforcement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="시행일자")
    promulgation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="공포일자")
    promulgation_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="공포번호")
    is_effective: Mapped[bool] = mapped_column(default=True, comment="현행 여부")
    
    # 내용
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="제정/개정 이유")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    articles: Mapped[list["LawArticle"]] = relationship("LawArticle", back_populates="law", cascade="all, delete-orphan")
    histories: Mapped[list["LawHistory"]] = relationship("LawHistory", back_populates="law", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_laws_type_name", "law_type", "law_name"),
    )
    
    def __repr__(self) -> str:
        return f"<Law(id={self.id}, law_name='{self.law_name}')>"


class LawArticle(Base):
    """
    법령 조문 테이블
    법령의 개별 조문 저장
    """
    __tablename__ = "law_articles"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 외래 키
    law_id: Mapped[int] = mapped_column(ForeignKey("laws.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 조문 정보
    article_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="조 번호 (예: 제1조)")
    article_title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="조 제목")
    article_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="조 내용")
    paragraph_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="항 번호")
    paragraph_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="항 내용")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 관계
    law: Mapped["Law"] = relationship("Law", back_populates="articles")
    
    __table_args__ = (
        Index("ix_law_articles_law_article", "law_id", "article_number"),
    )
    
    def __repr__(self) -> str:
        return f"<LawArticle(id={self.id}, article_number='{self.article_number}')>"


class LawTerm(Base):
    """
    법령 용어 테이블
    법령에서 사용되는 용어와 해석
    """
    __tablename__ = "law_terms"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 용어 식별
    term_serial_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="용어 일련번호")
    term: Mapped[str] = mapped_column(String(200), nullable=False, index=True, comment="용어")
    
    # 용어 정의
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="정의/해석")
    example: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="사용 예시")
    related_law: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="관련 법령")
    related_article: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="관련 조문")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<LawTerm(id={self.id}, term='{self.term}')>"


class LawHistory(Base):
    """
    법령 연혁 테이블
    법령의 제정/개정 이력
    """
    __tablename__ = "law_histories"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 외래 키
    law_id: Mapped[int] = mapped_column(ForeignKey("laws.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 연혁 정보
    history_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="연혁구분 (제정/일부개정/전부개정/폐지)")
    history_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="연혁일자")
    promulgation_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="공포번호")
    enforcement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="시행일자")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="개정이유")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 관계
    law: Mapped["Law"] = relationship("Law", back_populates="histories")
    
    __table_args__ = (
        Index("ix_law_histories_law_date", "law_id", "history_date"),
    )
    
    def __repr__(self) -> str:
        return f"<LawHistory(id={self.id}, history_type='{self.history_type}')>"
