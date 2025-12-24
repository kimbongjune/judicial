"""
통계 API 라우터
시스템 전체 통계 조회
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Case, ConstitutionalDecision, Interpretation, SearchLog

router = APIRouter(prefix="/api/stats", tags=["통계"])


class OverviewStats(BaseModel):
    """전체 통계 응답"""
    case_count: int
    constitutional_count: int
    interpretation_count: int
    total_count: int


class SearchStats(BaseModel):
    """검색 통계 응답"""
    total_searches: int
    today_searches: int
    avg_response_time_ms: Optional[float] = None


class RecentSearchResponse(BaseModel):
    """최근 검색어 응답"""
    query: str
    search_type: str
    result_count: int
    created_at: datetime


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(session: AsyncSession = Depends(get_session)):
    """
    전체 통계 조회
    - 판례 수
    - 헌재결정례 수
    - 법령해석례 수
    - 전체 문서 수
    """
    # 판례 수
    case_result = await session.execute(select(func.count()).select_from(Case))
    case_count = case_result.scalar() or 0
    
    # 헌재결정례 수
    constitutional_result = await session.execute(select(func.count()).select_from(ConstitutionalDecision))
    constitutional_count = constitutional_result.scalar() or 0
    
    # 법령해석례 수
    interpretation_result = await session.execute(select(func.count()).select_from(Interpretation))
    interpretation_count = interpretation_result.scalar() or 0
    
    return OverviewStats(
        case_count=case_count,
        constitutional_count=constitutional_count,
        interpretation_count=interpretation_count,
        total_count=case_count + constitutional_count + interpretation_count
    )


@router.get("/searches", response_model=SearchStats)
async def get_search_stats(session: AsyncSession = Depends(get_session)):
    """검색 통계 조회"""
    # 전체 검색 수
    total_result = await session.execute(select(func.count()).select_from(SearchLog))
    total_searches = total_result.scalar() or 0
    
    # 오늘 검색 수
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await session.execute(
        select(func.count()).select_from(SearchLog).where(SearchLog.created_at >= today)
    )
    today_searches = today_result.scalar() or 0
    
    # 평균 응답 시간
    avg_result = await session.execute(
        select(func.avg(SearchLog.response_time_ms)).where(SearchLog.response_time_ms.isnot(None))
    )
    avg_response_time_ms = avg_result.scalar()
    
    return SearchStats(
        total_searches=total_searches,
        today_searches=today_searches,
        avg_response_time_ms=round(avg_response_time_ms, 2) if avg_response_time_ms else None
    )


@router.get("/recent-searches", response_model=List[RecentSearchResponse])
async def get_recent_searches(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session)
):
    """최근 검색어 목록 조회"""
    result = await session.execute(
        select(SearchLog)
        .order_by(desc(SearchLog.created_at))
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return [
        RecentSearchResponse(
            query=log.query,
            search_type=log.search_type,
            result_count=log.result_count,
            created_at=log.created_at
        )
        for log in logs
    ]

