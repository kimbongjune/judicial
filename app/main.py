"""
법률 판례 검색 시스템 - FastAPI 메인 애플리케이션
"""
from contextlib import asynccontextmanager
from typing import Optional
from datetime import date
from fastapi import FastAPI, Request, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, get_session
from app.services import CaseService, ConstitutionalService, InterpretationService, SimilaritySearchService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # 시작 시 실행
    print("🚀 애플리케이션 시작...")
    await init_db()
    print("데이터베이스 초기화 완료")
    
    yield
    
    # 종료 시 실행
    print("👋 애플리케이션 종료...")


# FastAPI 앱 생성
app = FastAPI(
    title="법률 판례 검색 시스템",
    description="판례, 헌재결정례, 법령해석례 통합 검색 서비스",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 템플릿 설정
templates = Jinja2Templates(directory="app/templates")


# ===========================================
# 헬스체크 API
# ===========================================

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }


# ===========================================
# 페이지 라우트 (SSR)
# ===========================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: AsyncSession = Depends(get_session)):
    """메인 페이지"""
    from sqlalchemy import select, func
    from app.models import Case, ConstitutionalDecision, Interpretation
    
    # 통계 조회
    case_count_result = await session.execute(select(func.count()).select_from(Case))
    case_count = case_count_result.scalar() or 0
    
    constitutional_count_result = await session.execute(select(func.count()).select_from(ConstitutionalDecision))
    constitutional_count = constitutional_count_result.scalar() or 0
    
    interpretation_count_result = await session.execute(select(func.count()).select_from(Interpretation))
    interpretation_count = interpretation_count_result.scalar() or 0
    
    # 최근 판례 조회
    recent_cases_result = await session.execute(
        select(Case).order_by(Case.judgment_date.desc()).limit(4)
    )
    recent_cases = recent_cases_result.scalars().all()
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "case_count": f"{case_count:,}",
            "constitutional_count": f"{constitutional_count:,}",
            "interpretation_count": f"{interpretation_count:,}",
            "recent_cases": recent_cases
        }
    )


@app.get("/cases", response_class=HTMLResponse)
async def cases_list(
    request: Request,
    q: Optional[str] = None,
    court: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session)
):
    """판례 목록 페이지"""
    service = CaseService(session)
    result = await service.search_cases(
        q=q,
        court_name=court,
        case_type=case_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=20
    )
    
    # 필터 옵션
    courts = await service.get_distinct_courts()
    case_types = await service.get_distinct_case_types()
    
    return templates.TemplateResponse(
        "cases/list.html",
        {
            "request": request,
            "cases": result["items"],
            "query": q or "",
            "selected_courts": [court] if court else [],
            "selected_case_types": [case_type] if case_type else [],
            "date_from": date_from,
            "date_to": date_to,
            "page": result["page"],
            "total_pages": result["total_pages"],
            "total_count": result["total_count"],
            "courts": courts,
            "case_types": case_types
        }
    )


@app.get("/constitutional", response_class=HTMLResponse)
async def constitutional_list(
    request: Request,
    q: Optional[str] = None,
    case_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session)
):
    """헌재결정례 목록 페이지"""
    service = ConstitutionalService(session)
    result = await service.search_decisions(
        q=q,
        case_type=case_type,
        page=page,
        page_size=20
    )
    
    return templates.TemplateResponse(
        "constitutional/list.html",
        {
            "request": request,
            "decisions": result["items"],
            "q": q,
            "case_type": case_type,
            "page": result["page"],
            "total_pages": result["total_pages"],
            "total_count": result["total_count"]
        }
    )


@app.get("/interpretations", response_class=HTMLResponse)
async def interpretations_list(
    request: Request,
    q: Optional[str] = None,
    field: Optional[str] = None,
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session)
):
    """법령해석례 목록 페이지"""
    service = InterpretationService(session)
    result = await service.search_interpretations(
        q=q,
        field=field,
        page=page,
        page_size=20
    )
    
    return templates.TemplateResponse(
        "interpretations/list.html",
        {
            "request": request,
            "interpretations": result["items"],
            "q": q,
            "field": field,
            "page": result["page"],
            "total_pages": result["total_pages"],
            "total_count": result["total_count"]
        }
    )


@app.get("/similarity", response_class=HTMLResponse)
async def similarity_search(
    request: Request,
    q: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """유사 문서 검색 페이지"""
    similar_docs = []
    
    if q:
        service = SimilaritySearchService(session)
        results = await service.search_similar_cases(
            query=q,
            top_k=20,
            threshold=0.3
        )
        similar_docs = results
    
    return templates.TemplateResponse(
        "similarity/results.html",
        {
            "request": request,
            "similar_docs": similar_docs,
            "q": q,
            "source_doc": None,
            "doc_type": None
        }
    )


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request, session: AsyncSession = Depends(get_session)):
    """통계 대시보드 페이지"""
    from sqlalchemy import select, func, desc
    from app.models import Case, ConstitutionalDecision, Interpretation, SearchLog
    
    # 데이터 통계
    case_result = await session.execute(select(func.count()).select_from(Case))
    case_count = case_result.scalar() or 0
    
    constitutional_result = await session.execute(select(func.count()).select_from(ConstitutionalDecision))
    constitutional_count = constitutional_result.scalar() or 0
    
    interpretation_result = await session.execute(select(func.count()).select_from(Interpretation))
    interpretation_count = interpretation_result.scalar() or 0
    
    # 검색 통계
    total_search_result = await session.execute(select(func.count()).select_from(SearchLog))
    total_searches = total_search_result.scalar() or 0
    
    from datetime import datetime
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await session.execute(
        select(func.count()).select_from(SearchLog).where(SearchLog.created_at >= today)
    )
    today_searches = today_result.scalar() or 0
    
    avg_result = await session.execute(
        select(func.avg(SearchLog.response_time_ms)).where(SearchLog.response_time_ms.isnot(None))
    )
    avg_response_time = avg_result.scalar()
    
    # 최근 검색어
    recent_result = await session.execute(
        select(SearchLog).order_by(desc(SearchLog.created_at)).limit(10)
    )
    recent_searches = recent_result.scalars().all()
    
    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "case_count": f"{case_count:,}",
            "constitutional_count": f"{constitutional_count:,}",
            "interpretation_count": f"{interpretation_count:,}",
            "total_count": f"{case_count + constitutional_count + interpretation_count:,}",
            "total_searches": total_searches,
            "today_searches": today_searches,
            "avg_response_time": round(avg_response_time, 2) if avg_response_time else None,
            "recent_searches": recent_searches
        }
    )


# ===========================================
# API 라우터 등록
# ===========================================

from app.api import api_router
app.include_router(api_router)


# ===========================================
# 판례 상세 페이지 라우트
# ===========================================

@app.get("/cases/{case_id}", response_class=HTMLResponse)
async def case_detail(
    request: Request,
    case_id: int,
    session: AsyncSession = Depends(get_session)
):
    """판례 상세 페이지"""
    service = CaseService(session)
    case = await service.get_case_by_id(case_id)
    
    if not case:
        return templates.TemplateResponse(
            "cases/detail.html",
            {"request": request, "case": None, "error": "판례를 찾을 수 없습니다"}
        )
    
    # 목차 추출
    toc = service.extract_toc_from_content(case.full_text)
    
    # 요약 생성
    summary = service.summarize_case(case)
    
    return templates.TemplateResponse(
        "cases/detail.html",
        {
            "request": request,
            "case": case,
            "toc": toc,
            "summary": summary
        }
    )


# ===========================================
# 헌재결정례 상세 페이지 라우트
# ===========================================

@app.get("/constitutional/{decision_id}", response_class=HTMLResponse)
async def constitutional_detail(
    request: Request,
    decision_id: int,
    session: AsyncSession = Depends(get_session)
):
    """헌재결정례 상세 페이지"""
    service = ConstitutionalService(session)
    decision = await service.get_decision_by_id(decision_id)
    
    if not decision:
        return templates.TemplateResponse(
            "constitutional/detail.html",
            {"request": request, "decision": None, "error": "결정례를 찾을 수 없습니다"}
        )
    
    return templates.TemplateResponse(
        "constitutional/detail.html",
        {
            "request": request,
            "decision": decision
        }
    )


# ===========================================
# 법령해석례 상세 페이지 라우트
# ===========================================

@app.get("/interpretations/{interpretation_id}", response_class=HTMLResponse)
async def interpretation_detail(
    request: Request,
    interpretation_id: int,
    session: AsyncSession = Depends(get_session)
):
    """법령해석례 상세 페이지"""
    service = InterpretationService(session)
    interpretation = await service.get_interpretation_by_id(interpretation_id)
    
    if not interpretation:
        return templates.TemplateResponse(
            "interpretations/detail.html",
            {"request": request, "interpretation": None, "error": "해석례를 찾을 수 없습니다"}
        )
    
    return templates.TemplateResponse(
        "interpretations/detail.html",
        {
            "request": request,
            "interpretation": interpretation
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
    )
