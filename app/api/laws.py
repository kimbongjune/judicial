"""
법령 API 라우터
법령 조회, 조문, 연혁 등
"""
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.law_service import LawService

router = APIRouter(prefix="/api/laws", tags=["법령"])


class LawResponse(BaseModel):
    """법령 기본 응답"""
    id: int
    law_serial_number: int
    law_name: str
    law_type: Optional[str] = None
    ministry: Optional[str] = None
    enforcement_date: Optional[str] = None
    is_effective: bool = True
    
    class Config:
        from_attributes = True


class LawDetailResponse(LawResponse):
    """법령 상세 응답"""
    law_name_korean: Optional[str] = None
    law_name_abbreviated: Optional[str] = None
    promulgation_date: Optional[str] = None
    promulgation_number: Optional[str] = None
    purpose: Optional[str] = None


class LawArticleResponse(BaseModel):
    """법령 조문 응답"""
    id: int
    article_number: str
    article_title: Optional[str] = None
    article_content: Optional[str] = None
    paragraph_number: Optional[str] = None
    paragraph_content: Optional[str] = None


class LawHistoryResponse(BaseModel):
    """법령 연혁 응답"""
    id: int
    history_type: str
    history_date: Optional[str] = None
    promulgation_number: Optional[str] = None
    enforcement_date: Optional[str] = None
    reason: Optional[str] = None


class LawListResponse(BaseModel):
    """법령 목록 응답"""
    items: List[LawResponse]
    total_count: int
    page: int
    total_pages: int


@router.get("", response_model=LawListResponse)
async def search_laws(
    q: Optional[str] = Query(None, description="법령명 검색"),
    law_type: Optional[str] = Query(None, description="법령 구분 (법률/대통령령/부령)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """법령 검색"""
    service = LawService(session)
    result = await service.search_laws(
        q=q,
        law_type=law_type,
        page=page,
        page_size=page_size
    )
    
    items = []
    for law in result["items"]:
        items.append(LawResponse(
            id=law.id,
            law_serial_number=law.law_serial_number,
            law_name=law.law_name,
            law_type=law.law_type,
            ministry=law.ministry,
            enforcement_date=law.enforcement_date.strftime("%Y.%m.%d") if law.enforcement_date else None,
            is_effective=law.is_effective
        ))
    
    return LawListResponse(
        items=items,
        total_count=result["total_count"],
        page=result["page"],
        total_pages=result["total_pages"]
    )


@router.get("/{law_id}", response_model=LawDetailResponse)
async def get_law_detail(
    law_id: int,
    session: AsyncSession = Depends(get_session)
):
    """법령 상세 조회"""
    service = LawService(session)
    law = await service.get_law_by_id(law_id)
    
    if not law:
        raise HTTPException(status_code=404, detail="법령을 찾을 수 없습니다")
    
    return LawDetailResponse(
        id=law.id,
        law_serial_number=law.law_serial_number,
        law_name=law.law_name,
        law_name_korean=law.law_name_korean,
        law_name_abbreviated=law.law_name_abbreviated,
        law_type=law.law_type,
        ministry=law.ministry,
        enforcement_date=law.enforcement_date.strftime("%Y.%m.%d") if law.enforcement_date else None,
        promulgation_date=law.promulgation_date.strftime("%Y.%m.%d") if law.promulgation_date else None,
        promulgation_number=law.promulgation_number,
        is_effective=law.is_effective,
        purpose=law.purpose
    )


@router.get("/{law_id}/articles")
async def get_law_articles(
    law_id: int,
    session: AsyncSession = Depends(get_session)
):
    """법령 조문 목록 조회 (목차 역할)"""
    service = LawService(session)
    law = await service.get_law_by_id(law_id)
    
    if not law:
        raise HTTPException(status_code=404, detail="법령을 찾을 수 없습니다")
    
    articles = await service.get_law_articles(law_id)
    
    return {
        "law_id": law_id,
        "law_name": law.law_name,
        "total": len(articles),
        "articles": [
            LawArticleResponse(
                id=a.id,
                article_number=a.article_number,
                article_title=a.article_title,
                article_content=a.article_content,
                paragraph_number=a.paragraph_number,
                paragraph_content=a.paragraph_content
            )
            for a in articles
        ]
    }


@router.get("/{law_id}/history")
async def get_law_history(
    law_id: int,
    session: AsyncSession = Depends(get_session)
):
    """법령 연혁 조회"""
    service = LawService(session)
    law = await service.get_law_by_id(law_id)
    
    if not law:
        raise HTTPException(status_code=404, detail="법령을 찾을 수 없습니다")
    
    histories = await service.get_law_history(law_id)
    
    return {
        "law_id": law_id,
        "law_name": law.law_name,
        "total": len(histories),
        "histories": [
            LawHistoryResponse(
                id=h.id,
                history_type=h.history_type,
                history_date=h.history_date.strftime("%Y.%m.%d") if h.history_date else None,
                promulgation_number=h.promulgation_number,
                enforcement_date=h.enforcement_date.strftime("%Y.%m.%d") if h.enforcement_date else None,
                reason=h.reason
            )
            for h in histories
        ]
    }


@router.get("/{law_id}/articles/{article_number}")
async def get_law_article(
    law_id: int,
    article_number: str,
    session: AsyncSession = Depends(get_session)
):
    """특정 조문 조회"""
    service = LawService(session)
    article = await service.get_article_by_number(law_id, article_number)
    
    if not article:
        raise HTTPException(status_code=404, detail="조문을 찾을 수 없습니다")
    
    return LawArticleResponse(
        id=article.id,
        article_number=article.article_number,
        article_title=article.article_title,
        article_content=article.article_content,
        paragraph_number=article.paragraph_number,
        paragraph_content=article.paragraph_content
    )
