"""
법령 서비스
법령 조회, 연혁, 조문 관련 비즈니스 로직
"""
import re
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.law import Law, LawArticle, LawHistory, LawTerm


class LawService:
    """법령 관련 서비스"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_laws(
        self,
        q: Optional[str] = None,
        law_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """법령 검색"""
        query = select(Law)
        count_query = select(func.count()).select_from(Law)
        
        conditions = []
        
        if q:
            search_term = f"%{q}%"
            conditions.append(Law.law_name.ilike(search_term))
        
        if law_type:
            conditions.append(Law.law_type == law_type)
        
        if conditions:
            from sqlalchemy import and_
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar() or 0
        
        offset = (page - 1) * page_size
        query = query.order_by(Law.law_name).offset(offset).limit(page_size)
        
        result = await self.session.execute(query)
        laws = result.scalars().all()
        
        return {
            "items": laws,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    async def get_law_by_id(self, law_id: int) -> Optional[Law]:
        """ID로 법령 조회"""
        result = await self.session.execute(
            select(Law).where(Law.id == law_id)
        )
        return result.scalar_one_or_none()
    
    async def get_law_by_serial_number(self, serial_number: int) -> Optional[Law]:
        """일련번호로 법령 조회"""
        result = await self.session.execute(
            select(Law).where(Law.law_serial_number == serial_number)
        )
        return result.scalar_one_or_none()
    
    async def get_law_by_name(self, law_name: str) -> Optional[Law]:
        """법령명으로 조회 (부분 일치)"""
        result = await self.session.execute(
            select(Law).where(Law.law_name.ilike(f"%{law_name}%")).limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_law_articles(self, law_id: int) -> List[LawArticle]:
        """법령의 조문 목록 조회"""
        result = await self.session.execute(
            select(LawArticle)
            .where(LawArticle.law_id == law_id)
            .order_by(LawArticle.article_number)
        )
        return result.scalars().all()
    
    async def get_law_history(self, law_id: int) -> List[LawHistory]:
        """법령의 연혁 조회"""
        result = await self.session.execute(
            select(LawHistory)
            .where(LawHistory.law_id == law_id)
            .order_by(LawHistory.history_date.desc())
        )
        return result.scalars().all()
    
    async def get_article_by_number(
        self, 
        law_id: int, 
        article_number: str
    ) -> Optional[LawArticle]:
        """특정 조문 조회"""
        result = await self.session.execute(
            select(LawArticle)
            .where(LawArticle.law_id == law_id)
            .where(LawArticle.article_number == article_number)
        )
        return result.scalar_one_or_none()
    
    def parse_reference_provisions(self, reference_text: str) -> List[Dict[str, str]]:
        """
        참조조문 텍스트 파싱
        
        예: "민법 제750조, 제751조, 형법 제250조"
        → [{"law_name": "민법", "article": "제750조"}, ...]
        """
        if not reference_text:
            return []
        
        provisions = []
        current_law = None
        
        # 법령명과 조문 패턴
        # "민법 제750조", "동법 제751조", "제752조" 등
        pattern = r'([가-힣]+법(?:\s*시행령|\s*시행규칙)?)\s*(제\d+조(?:의\d+)?(?:\s*제\d+항)?)|(?:동법\s*)?(제\d+조(?:의\d+)?(?:\s*제\d+항)?)'
        
        matches = re.findall(pattern, reference_text)
        
        for match in matches:
            law_name = match[0] if match[0] else current_law
            article = match[1] if match[1] else match[2] if len(match) > 2 else ""
            
            if law_name:
                current_law = law_name
            
            if article and current_law:
                provisions.append({
                    "law_name": current_law,
                    "article": article.strip()
                })
        
        return provisions


class LawTermService:
    """법령용어 서비스"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_terms(
        self,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """법령용어 검색"""
        query = select(LawTerm)
        count_query = select(func.count()).select_from(LawTerm)
        
        if q:
            search_term = f"%{q}%"
            query = query.where(LawTerm.term.ilike(search_term))
            count_query = count_query.where(LawTerm.term.ilike(search_term))
        
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar() or 0
        
        offset = (page - 1) * page_size
        query = query.order_by(LawTerm.term).offset(offset).limit(page_size)
        
        result = await self.session.execute(query)
        terms = result.scalars().all()
        
        return {
            "items": terms,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    async def get_term(self, term: str) -> Optional[LawTerm]:
        """정확한 용어 조회"""
        result = await self.session.execute(
            select(LawTerm).where(LawTerm.term == term)
        )
        return result.scalar_one_or_none()
    
    async def get_terms_in_text(self, text: str) -> List[LawTerm]:
        """
        텍스트에서 법령용어 감지
        텍스트 내에 존재하는 모든 법령용어를 찾아 반환
        """
        if not text:
            return []
        
        # 모든 법령용어 조회
        result = await self.session.execute(select(LawTerm))
        all_terms = result.scalars().all()
        
        found_terms = []
        for term in all_terms:
            if term.term in text:
                found_terms.append(term)
        
        return found_terms
    
    async def get_all_terms_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 법령용어를 딕셔너리로 반환 (프론트엔드 캐싱용)
        """
        result = await self.session.execute(select(LawTerm))
        terms = result.scalars().all()
        
        return {
            term.term: {
                "term": term.term,
                "definition": term.definition,
                "example": term.example,
                "related_law": term.related_law,
                "related_article": term.related_article
            }
            for term in terms
        }
