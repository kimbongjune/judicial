"""
북마크 API 라우터
세션 기반 북마크 관리
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.bookmark import Bookmark
from app.models import Case, ConstitutionalDecision, Interpretation

router = APIRouter(prefix="/api/bookmarks", tags=["북마크"])


class BookmarkCreate(BaseModel):
    """북마크 생성 요청"""
    session_id: str
    entity_type: str  # 'case', 'constitutional', 'interpretation'
    entity_id: int
    entity_title: Optional[str] = None
    entity_number: Optional[str] = None


class BookmarkResponse(BaseModel):
    """북마크 응답"""
    id: int
    session_id: str
    entity_type: str
    entity_id: int
    entity_title: Optional[str] = None
    entity_number: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BookmarkListResponse(BaseModel):
    """북마크 목록 응답"""
    items: List[BookmarkResponse]
    total: int


@router.post("", response_model=BookmarkResponse)
async def create_bookmark(
    bookmark: BookmarkCreate,
    session: AsyncSession = Depends(get_session)
):
    """북마크 추가"""
    # 유효한 entity_type 검증
    if bookmark.entity_type not in ['case', 'constitutional', 'interpretation']:
        raise HTTPException(status_code=400, detail="잘못된 entity_type입니다")
    
    # 중복 체크
    existing = await session.execute(
        select(Bookmark).where(
            and_(
                Bookmark.session_id == bookmark.session_id,
                Bookmark.entity_type == bookmark.entity_type,
                Bookmark.entity_id == bookmark.entity_id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 북마크에 추가되어 있습니다")
    
    # 엔티티 정보 조회 (title, number 캐싱)
    entity_title = bookmark.entity_title
    entity_number = bookmark.entity_number
    
    if not entity_title:
        if bookmark.entity_type == 'case':
            result = await session.execute(
                select(Case).where(Case.id == bookmark.entity_id)
            )
            entity = result.scalar_one_or_none()
            if entity:
                entity_title = entity.case_name
                entity_number = entity.case_number
        elif bookmark.entity_type == 'constitutional':
            result = await session.execute(
                select(ConstitutionalDecision).where(ConstitutionalDecision.id == bookmark.entity_id)
            )
            entity = result.scalar_one_or_none()
            if entity:
                entity_title = entity.case_name
                entity_number = entity.case_number
        elif bookmark.entity_type == 'interpretation':
            result = await session.execute(
                select(Interpretation).where(Interpretation.id == bookmark.entity_id)
            )
            entity = result.scalar_one_or_none()
            if entity:
                entity_title = entity.agenda_name
                entity_number = entity.agenda_number
    
    new_bookmark = Bookmark(
        session_id=bookmark.session_id,
        entity_type=bookmark.entity_type,
        entity_id=bookmark.entity_id,
        entity_title=entity_title,
        entity_number=entity_number
    )
    session.add(new_bookmark)
    await session.commit()
    await session.refresh(new_bookmark)
    
    return new_bookmark


@router.delete("")
async def delete_bookmark(
    session_id: str = Query(...),
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """북마크 제거"""
    result = await session.execute(
        select(Bookmark).where(
            and_(
                Bookmark.session_id == session_id,
                Bookmark.entity_type == entity_type,
                Bookmark.entity_id == entity_id
            )
        )
    )
    bookmark = result.scalar_one_or_none()
    
    if not bookmark:
        raise HTTPException(status_code=404, detail="북마크를 찾을 수 없습니다")
    
    await session.delete(bookmark)
    await session.commit()
    
    return {"message": "북마크가 삭제되었습니다"}


@router.get("", response_model=BookmarkListResponse)
async def list_bookmarks(
    session_id: str = Query(...),
    entity_type: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """북마크 목록 조회"""
    query = select(Bookmark).where(Bookmark.session_id == session_id)
    
    if entity_type:
        query = query.where(Bookmark.entity_type == entity_type)
    
    query = query.order_by(Bookmark.created_at.desc())
    
    result = await session.execute(query)
    bookmarks = result.scalars().all()
    
    return BookmarkListResponse(
        items=bookmarks,
        total=len(bookmarks)
    )


@router.get("/check")
async def check_bookmark(
    session_id: str = Query(...),
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """북마크 여부 확인"""
    result = await session.execute(
        select(Bookmark).where(
            and_(
                Bookmark.session_id == session_id,
                Bookmark.entity_type == entity_type,
                Bookmark.entity_id == entity_id
            )
        )
    )
    bookmark = result.scalar_one_or_none()
    
    return {"bookmarked": bookmark is not None}
