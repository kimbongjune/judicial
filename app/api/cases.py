"""
판례 API 라우터
"""
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.case_service import CaseService

router = APIRouter(prefix="/api/cases", tags=["판례"])


class CaseResponse(BaseModel):
    """판례 응답 모델"""
    id: int
    case_serial_number: int
    case_number: str
    case_name: str
    court_name: str
    case_type_name: Optional[str] = None
    judgment_type: Optional[str] = None
    judgment_date: Optional[str] = None
    summary: Optional[str] = None
    gist: Optional[str] = None
    
    class Config:
        from_attributes = True


class CaseDetailResponse(CaseResponse):
    """판례 상세 응답"""
    reference_provisions: Optional[str] = None
    reference_cases: Optional[str] = None
    full_text: Optional[str] = None


class CaseListResponse(BaseModel):
    """판례 목록 응답"""
    items: List[CaseResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class CaseSummaryResponse(BaseModel):
    """판례 요약 응답 모델"""
    case_id: int
    summary: str


class TocItem(BaseModel):
    """목차 항목"""
    title: str
    level: int
    line_number: int


@router.get("", response_model=CaseListResponse)
async def search_cases(
    q: Optional[str] = Query(None, description="검색어"),
    court_name: Optional[str] = Query(None, description="법원명"),
    case_type: Optional[str] = Query(None, description="사건종류"),
    date_from: Optional[date] = Query(None, description="시작일"),
    date_to: Optional[date] = Query(None, description="종료일"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """
    판례 검색 API
    
    - 텍스트 검색: 사건명, 판시사항, 판결요지에서 검색
    - 필터: 법원명, 사건종류, 날짜 범위
    """
    service = CaseService(session)
    result = await service.search_cases(
        q=q,
        court_name=court_name,
        case_type=case_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size
    )
    
    items = []
    for case in result["items"]:
        items.append(CaseResponse(
            id=case.id,
            case_serial_number=case.case_serial_number,
            case_number=case.case_number,
            case_name=case.case_name,
            court_name=case.court_name,
            case_type_name=case.case_type_name,
            judgment_type=case.judgment_type,
            judgment_date=case.judgment_date.strftime("%Y.%m.%d") if case.judgment_date else None,
            summary=case.summary[:200] + "..." if case.summary and len(case.summary) > 200 else case.summary,
            gist=case.gist[:200] + "..." if case.gist and len(case.gist) > 200 else case.gist
        ))
    
    return CaseListResponse(
        items=items,
        total_count=result["total_count"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"]
    )


@router.get("/filters")
async def get_search_filters(session: AsyncSession = Depends(get_session)):
    """
    검색 필터 옵션 조회
    - 법원 목록
    - 사건종류 목록
    """
    service = CaseService(session)
    courts = await service.get_distinct_courts()
    case_types = await service.get_distinct_case_types()
    
    return {
        "courts": courts,
        "case_types": case_types
    }


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case_detail(
    case_id: int,
    session: AsyncSession = Depends(get_session)
):
    """판례 상세 조회"""
    service = CaseService(session)
    case = await service.get_case_by_id(case_id)
    
    if not case:
        raise HTTPException(status_code=404, detail="판례를 찾을 수 없습니다")
    
    return CaseDetailResponse(
        id=case.id,
        case_serial_number=case.case_serial_number,
        case_number=case.case_number,
        case_name=case.case_name,
        court_name=case.court_name,
        case_type_name=case.case_type_name,
        judgment_type=case.judgment_type,
        judgment_date=case.judgment_date.strftime("%Y.%m.%d") if case.judgment_date else None,
        summary=case.summary,
        gist=case.gist,
        reference_provisions=case.reference_provisions,
        reference_cases=case.reference_cases,
        full_text=case.full_text
    )


@router.get("/{case_id}/summary", response_model=CaseSummaryResponse)
async def get_case_summary(
    case_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    판례 본문 요약 API
    """
    service = CaseService(session)
    case = await service.get_case_by_id(case_id)
    
    if not case:
        raise HTTPException(status_code=404, detail="판례를 찾을 수 없습니다")
    
    summary = service.summarize_case(case)
    
    return CaseSummaryResponse(
        case_id=case_id,
        summary=summary
    )


@router.get("/{case_id}/toc")
async def get_case_toc(
    case_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    판례 목차 조회
    """
    service = CaseService(session)
    case = await service.get_case_by_id(case_id)
    
    if not case:
        raise HTTPException(status_code=404, detail="판례를 찾을 수 없습니다")
    
    toc = service.extract_toc_from_content(case.full_text)
    
    return {
        "case_id": case_id,
        "toc": toc
    }


class ReferenceProvisionResponse(BaseModel):
    """참조조문 응답"""
    provision: str
    law_name: str
    article_number: str
    content: Optional[str] = None
    law_id: Optional[int] = None


@router.get("/{case_id}/reference-provisions")
async def get_reference_provisions(
    case_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    판례의 참조조문 목록 조회
    """
    from app.services.law_service import LawService
    
    case_service = CaseService(session)
    law_service = LawService(session)
    
    case = await case_service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="판례를 찾을 수 없습니다")
    
    # 참조조문 파싱
    parsed = law_service.parse_reference_provisions(case.reference_provisions or "")
    
    provisions = []
    for item in parsed:
        law = await law_service.get_law_by_name(item["law_name"])
        law_id = law.id if law else None
        
        # 조문 내용 조회 시도
        content = None
        if law:
            article = await law_service.get_article_by_number(law.id, item["article"])
            if article:
                content = article.article_content
        
        provisions.append(ReferenceProvisionResponse(
            provision=f"{item['law_name']} {item['article']}",
            law_name=item["law_name"],
            article_number=item["article"],
            content=content,
            law_id=law_id
        ))
    
    return {
        "case_id": case_id,
        "total": len(provisions),
        "provisions": provisions
    }


class ReferenceCaseResponse(BaseModel):
    """참조판례 응답"""
    case_number: str
    case_name: Optional[str] = None
    court_name: Optional[str] = None
    judgment_date: Optional[str] = None
    case_id: Optional[int] = None


@router.get("/{case_id}/reference-cases")
async def get_reference_cases(
    case_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    판례의 참조판례 목록 조회
    """
    import re
    from sqlalchemy import select
    from app.models.case import Case
    
    service = CaseService(session)
    case = await service.get_case_by_id(case_id)
    
    if not case:
        raise HTTPException(status_code=404, detail="판례를 찾을 수 없습니다")
    
    ref_cases_text = case.reference_cases or ""
    
    # 참조판례 파싱 (예: "대법원 2020. 1. 1. 선고 2019다12345 판결")
    pattern = r'(대법원|서울고등법원|[가-힣]+법원)?\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*선고\s*(\d+[가-힣]+\d+)\s*판결'
    
    matches = re.findall(pattern, ref_cases_text)
    
    ref_cases = []
    for match in matches:
        court = match[0] or "대법원"
        year, month, day = match[1], match[2], match[3]
        case_num = match[4]
        
        # DB에서 해당 판례 찾기 시도
        result = await session.execute(
            select(Case).where(Case.case_number.ilike(f"%{case_num}%")).limit(1)
        )
        found_case = result.scalar_one_or_none()
        
        ref_cases.append(ReferenceCaseResponse(
            case_number=case_num,
            case_name=found_case.case_name if found_case else None,
            court_name=court,
            judgment_date=f"{year}.{month}.{day}",
            case_id=found_case.id if found_case else None
        ))
    
    return {
        "case_id": case_id,
        "total": len(ref_cases),
        "cases": ref_cases
    }

