"""
API 라우터 패키지
"""
from fastapi import APIRouter
from app.api.law_terms import router as law_terms_router
from app.api.cases import router as cases_router
from app.api.laws import router as laws_router
from app.api.similarity import router as similarity_router

api_router = APIRouter()

# 라우터 등록
api_router.include_router(law_terms_router)
api_router.include_router(cases_router)
api_router.include_router(laws_router)
api_router.include_router(similarity_router)

__all__ = ["api_router"]
