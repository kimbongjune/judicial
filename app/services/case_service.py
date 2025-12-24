"""
판례 서비스
DB 조회, FAISS 유사도 검색 등 비즈니스 로직
"""
import re
from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.constitutional import ConstitutionalDecision
from app.models.interpretation import Interpretation


class CaseService:
    """판례 관련 서비스"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_cases(
        self,
        q: Optional[str] = None,
        court_name: Optional[str] = None,
        case_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        판례 검색 (텍스트 + 필터)
        """
        query = select(Case)
        count_query = select(func.count()).select_from(Case)
        
        conditions = []
        
        # 텍스트 검색
        if q:
            search_term = f"%{q}%"
            text_condition = or_(
                Case.case_name.ilike(search_term),
                Case.summary.ilike(search_term),
                Case.gist.ilike(search_term),
                Case.case_number.ilike(search_term)
            )
            conditions.append(text_condition)
        
        # 법원 필터
        if court_name:
            conditions.append(Case.court_name == court_name)
        
        # 사건종류 필터
        if case_type:
            conditions.append(Case.case_type_name == case_type)
        
        # 날짜 범위 필터
        if date_from:
            conditions.append(Case.judgment_date >= date_from)
        if date_to:
            conditions.append(Case.judgment_date <= date_to)
        
        # 조건 적용
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 전체 건수
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar() or 0
        
        # 페이징
        offset = (page - 1) * page_size
        query = query.order_by(Case.judgment_date.desc()).offset(offset).limit(page_size)
        
        result = await self.session.execute(query)
        cases = result.scalars().all()
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "items": cases,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    
    async def get_case_by_id(self, case_id: int) -> Optional[Case]:
        """ID로 판례 조회"""
        result = await self.session.execute(
            select(Case).where(Case.id == case_id)
        )
        return result.scalar_one_or_none()
    
    async def get_case_by_serial_number(self, serial_number: int) -> Optional[Case]:
        """일련번호로 판례 조회"""
        result = await self.session.execute(
            select(Case).where(Case.case_serial_number == serial_number)
        )
        return result.scalar_one_or_none()
    
    async def get_distinct_courts(self) -> List[str]:
        """법원 목록 조회"""
        result = await self.session.execute(
            select(Case.court_name).distinct().where(Case.court_name.isnot(None))
        )
        return [row[0] for row in result.all() if row[0]]
    
    async def get_distinct_case_types(self) -> List[str]:
        """사건종류 목록 조회"""
        result = await self.session.execute(
            select(Case.case_type_name).distinct().where(Case.case_type_name.isnot(None))
        )
        return [row[0] for row in result.all() if row[0]]
    
    def extract_toc_from_content(self, content: str) -> List[Dict[str, str]]:
        """
        판례 본문에서 목차 추출
        """
        if not content:
            return []
        
        toc = []
        
        # 주요 섹션 패턴
        patterns = [
            (r'【(주\s*문|이\s*유|결\s*론|판\s*결|참조조문|참조판례)】', 1),
            (r'\[?(주문|이유|결론|판결)\]?', 1),
            (r'^(\d+\.\s*[가-힣]+)', 2),  # "1. 사건의 개요" 형태
            (r'^([가-하]\.\s*[가-힣]+)', 2),  # "가. 기초사실" 형태
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            for pattern, level in patterns:
                match = re.match(pattern, line)
                if match:
                    title = match.group(1) if match.groups() else line[:50]
                    toc.append({
                        "title": title,
                        "level": level,
                        "line_number": i + 1
                    })
                    break
        
        return toc
    
    def summarize_case(self, case: Case) -> str:
        """
        판례 본문 요약 (규칙 기반)
        판시사항/판결요지가 있으면 그것을 활용, 없으면 본문에서 추출
        """
        # 이미 요약이 있으면 활용
        if case.gist:
            # 판결요지에서 핵심 부분 추출 (처음 500자)
            gist = case.gist.strip()
            if len(gist) > 500:
                # 문장 단위로 자르기
                sentences = re.split(r'(?<=[.。])\s*', gist)
                summary_parts = []
                current_len = 0
                for s in sentences:
                    if current_len + len(s) > 500:
                        break
                    summary_parts.append(s)
                    current_len += len(s)
                return ' '.join(summary_parts)
            return gist
        
        if case.summary:
            summary = case.summary.strip()
            if len(summary) > 300:
                return summary[:300] + "..."
            return summary
        
        # 본문에서 추출
        if case.full_text:
            # 이유 부분 찾기
            text = case.full_text
            reason_match = re.search(r'【이\s*유】(.+?)(?=【|$)', text, re.DOTALL)
            if reason_match:
                reason = reason_match.group(1).strip()[:500]
                return f"[이유 요약] {reason}..."
            
            # 처음 300자
            return text[:300] + "..."
        
        return "요약 정보가 없습니다."


class ConstitutionalService:
    """헌재결정례 서비스"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_decisions(
        self,
        q: Optional[str] = None,
        case_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """헌재결정례 검색"""
        query = select(ConstitutionalDecision)
        count_query = select(func.count()).select_from(ConstitutionalDecision)
        
        conditions = []
        
        if q:
            search_term = f"%{q}%"
            text_condition = or_(
                ConstitutionalDecision.case_name.ilike(search_term),
                ConstitutionalDecision.summary.ilike(search_term),
                ConstitutionalDecision.case_number.ilike(search_term)
            )
            conditions.append(text_condition)
        
        if case_type:
            conditions.append(ConstitutionalDecision.case_type_name == case_type)
        
        if date_from:
            conditions.append(ConstitutionalDecision.decision_date >= date_from)
        if date_to:
            conditions.append(ConstitutionalDecision.decision_date <= date_to)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar() or 0
        
        offset = (page - 1) * page_size
        query = query.order_by(ConstitutionalDecision.decision_date.desc()).offset(offset).limit(page_size)
        
        result = await self.session.execute(query)
        decisions = result.scalars().all()
        
        return {
            "items": decisions,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    async def get_decision_by_id(self, decision_id: int) -> Optional[ConstitutionalDecision]:
        result = await self.session.execute(
            select(ConstitutionalDecision).where(ConstitutionalDecision.id == decision_id)
        )
        return result.scalar_one_or_none()


class InterpretationService:
    """법령해석례 서비스"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_interpretations(
        self,
        q: Optional[str] = None,
        field: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """법령해석례 검색"""
        query = select(Interpretation)
        count_query = select(func.count()).select_from(Interpretation)
        
        conditions = []
        
        if q:
            search_term = f"%{q}%"
            text_condition = or_(
                Interpretation.agenda_name.ilike(search_term),
                Interpretation.question_summary.ilike(search_term),
                Interpretation.answer.ilike(search_term)
            )
            conditions.append(text_condition)
        
        if field:
            conditions.append(Interpretation.field == field)
        
        if date_from:
            conditions.append(Interpretation.reply_date >= date_from)
        if date_to:
            conditions.append(Interpretation.reply_date <= date_to)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar() or 0
        
        offset = (page - 1) * page_size
        query = query.order_by(Interpretation.reply_date.desc()).offset(offset).limit(page_size)
        
        result = await self.session.execute(query)
        interpretations = result.scalars().all()
        
        return {
            "items": interpretations,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    async def get_interpretation_by_id(self, interpretation_id: int) -> Optional[Interpretation]:
        result = await self.session.execute(
            select(Interpretation).where(Interpretation.id == interpretation_id)
        )
        return result.scalar_one_or_none()
