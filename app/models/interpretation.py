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
    법제처 OpenAPI의 법령해석례 데이터 저장
    """
    __tablename__ = "interpretations"
    
    # 기본 키
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 해석례 식별 정보
    법령해석례일련번호: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="법제처 법령해석례 고유 일련번호")
    안건번호: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="안건번호")
    
    # 분류 정보
    분야: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, comment="분야 (일반행정, 조세, 환경 등)")
    법령구분명: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="법령구분명")
    
    # 날짜 정보
    회신일자: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True, comment="회신일자")
    
    # 해석례 내용
    안건명: Mapped[str] = mapped_column(String(500), nullable=False, comment="해석례 제목/안건명")
    질의요지: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="질의요지 내용")
    회답: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="회답 내용")
    이유: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="해석 이유")
    참조조문: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조조문 목록")
    참조판례: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="참조판례 목록")
    비고: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="비고 사항")
    
    # 메타데이터
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="데이터 생성 시간")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="데이터 수정 시간")
    
    # 복합 인덱스
    __table_args__ = (
        Index("ix_interpretations_분야_회신일자", "분야", "회신일자"),
    )
    
    def __repr__(self) -> str:
        return f"<Interpretation(id={self.id}, 안건번호='{self.안건번호}', 안건명='{self.안건명[:30]}...')>"
    
    @property
    def search_text(self) -> str:
        """유사도 검색용 텍스트 생성"""
        parts = []
        if self.안건명:
            parts.append(self.안건명)
        if self.질의요지:
            parts.append(self.질의요지)
        if self.회답:
            parts.append(self.회답)
        return " ".join(parts)
