"""
유사도 검색 API 라우터
FAISS 벡터 검색
"""
from typing import Optional, List
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.search_service import SimilaritySearchService

router = APIRouter(prefix="/api/similarity", tags=["유사도검색"])


class SimilarCaseResponse(BaseModel):
    """유사 판례 응답"""
    id: int
    case_number: str
    case_name: str
    court_name: str
    judgment_date: Optional[str] = None
    similarity_score: float
    summary_preview: Optional[str] = None


class SimilaritySearchResponse(BaseModel):
    """유사도 검색 응답"""
    query: str
    total: int
    items: List[SimilarCaseResponse]


@router.get("/search", response_model=SimilaritySearchResponse)
async def search_similar(
    q: str = Query(..., min_length=1, description="검색 쿼리"),
    top_k: int = Query(10, ge=1, le=50, description="반환할 결과 수"),
    threshold: float = Query(0.3, ge=0, le=1, description="유사도 임계값"),
    session: AsyncSession = Depends(get_session)
):
    """
    텍스트 기반 유사 판례 검색
    
    입력된 텍스트와 가장 유사한 판례를 벡터 유사도 기반으로 검색합니다.
    """
    service = SimilaritySearchService(session)
    results = await service.search_similar_cases(
        query=q,
        top_k=top_k,
        threshold=threshold
    )
    
    items = []
    for result in results:
        case = result["case"]
        items.append(SimilarCaseResponse(
            id=case.id,
            case_number=case.case_number,
            case_name=case.case_name,
            court_name=case.court_name,
            judgment_date=case.judgment_date.strftime("%Y.%m.%d") if case.judgment_date else None,
            similarity_score=result["similarity_score"],
            summary_preview=case.summary[:150] + "..." if case.summary and len(case.summary) > 150 else case.summary
        ))
    
    return SimilaritySearchResponse(
        query=q,
        total=len(items),
        items=items
    )


@router.get("/by-case/{case_id}")
async def search_similar_by_case(
    case_id: int,
    top_k: int = Query(5, ge=1, le=20),
    session: AsyncSession = Depends(get_session)
):
    """
    특정 판례와 유사한 다른 판례 검색
    """
    service = SimilaritySearchService(session)
    results = await service.search_by_case_id(case_id, top_k=top_k)
    
    items = []
    for result in results:
        case = result["case"]
        items.append({
            "id": case.id,
            "case_number": case.case_number,
            "case_name": case.case_name,
            "court_name": case.court_name,
            "judgment_date": case.judgment_date.strftime("%Y.%m.%d") if case.judgment_date else None,
            "similarity_score": result["similarity_score"]
        })
    
    return {
        "source_case_id": case_id,
        "total": len(items),
        "similar_cases": items
    }


@router.get("/stats")
async def get_similarity_stats(session: AsyncSession = Depends(get_session)):
    """
    유사도 검색 인덱스 통계
    """
    service = SimilaritySearchService(session)
    return await service.get_index_stats()
