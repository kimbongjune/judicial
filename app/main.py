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
    print("✅ 데이터베이스 초기화 완료")
    
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
async def index(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.get("/cases", response_class=HTMLResponse)
async def cases_list(
    request: Request,
    q: Optional[str] = None,
    court_name: Optional[str] = None,
    case_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session)
):
    """판례 목록 페이지"""
    service = CaseService(session)
    result = await service.search_cases(
        q=q,
        court_name=court_name,
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
            "q": q,
            "court_name": court_name,
            "case_type": case_type,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
    )
