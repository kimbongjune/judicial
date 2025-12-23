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
    결정례일련번호: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="법제처 결정례 고유 일련번호")
    사건번호: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="사건번호 (예: 2023헌바123)")
    사건종류코드: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="사건종류코드")
    사건종류명: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, comment="사건종류명 (헌마, 헌바, 헌가 등)")
    
    # 날짜 정보
    선고일: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True, comment="선고일자")
    
    # 결정례 내용
    사건명: Mapped[str] = mapped_column(String(500), nullable=False, comment="결정례 제목/사건명")
    판례결과: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="결정 결과 (위헌, 합헌, 각하 등)")
    주문: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="주문 내용")
    이유: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="결정 이유")
    결정요지: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="결정요지 요약")
    참조조문: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조조문 목록")
    참조판례: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조판례 목록")
    결정문: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="결정문 전문")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="데이터 생성 시간")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="데이터 수정 시간")
    
    # 복합 인덱스
    __table_args__ = (
        Index("ix_constitutional_decisions_사건종류명_선고일", "사건종류명", "선고일"),
        Index("ix_constitutional_decisions_판례결과", "판례결과"),
    )
    
    def __repr__(self) -> str:
        return f"<ConstitutionalDecision(id={self.id}, 사건번호='{self.사건번호}', 사건명='{self.사건명[:30]}...')>"
    
    @property
    def search_text(self) -> str:
        """유사도 검색용 텍스트 생성"""
        parts = []
        if self.사건명:
            parts.append(self.사건명)
        if self.결정요지:
            parts.append(self.결정요지)
        if self.주문:
            parts.append(self.주문)
        return " ".join(parts)
