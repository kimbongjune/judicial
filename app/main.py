"""
법률 판례 검색 시스템 - FastAPI 메인 애플리케이션
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import init_db


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
async def cases_list(request: Request):
    """판례 목록 페이지"""
    return templates.TemplateResponse(
        "cases/list.html",
        {"request": request, "cases": [], "q": None, "page": 1, "total_pages": 0, "total_count": 0}
    )


@app.get("/constitutional", response_class=HTMLResponse)
async def constitutional_list(request: Request):
    """헌재결정례 목록 페이지"""
    return templates.TemplateResponse(
        "constitutional/list.html",
        {"request": request, "decisions": [], "q": None, "page": 1, "total_pages": 0, "total_count": 0}
    )


@app.get("/interpretations", response_class=HTMLResponse)
async def interpretations_list(request: Request):
    """법령해석례 목록 페이지"""
    return templates.TemplateResponse(
        "interpretations/list.html",
        {"request": request, "interpretations": [], "q": None, "page": 1, "total_pages": 0, "total_count": 0}
    )


@app.get("/similarity", response_class=HTMLResponse)
async def similarity_search(request: Request):
    """유사 문서 검색 페이지"""
    return templates.TemplateResponse(
        "similarity/results.html",
        {"request": request, "similar_docs": [], "source_doc": None, "doc_type": None}
    )


# ===========================================
# API 라우터 등록
# ===========================================

# from app.api import cases, constitutional, interpretations, search, similarity
# app.include_router(cases.router, prefix="/api/v1/cases", tags=["판례"])
# app.include_router(constitutional.router, prefix="/api/v1/constitutional", tags=["헌재결정례"])
# app.include_router(interpretations.router, prefix="/api/v1/interpretations", tags=["법령해석례"])
# app.include_router(search.router, prefix="/api/v1/search", tags=["검색"])
# app.include_router(similarity.router, prefix="/api/v1/similarity", tags=["유사검색"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
    )
