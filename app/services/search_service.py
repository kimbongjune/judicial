"""
유사도 검색 서비스
FAISS 인덱스를 활용한 벡터 유사도 검색
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.case import Case
from app.models.constitutional import ConstitutionalDecision
from app.models.interpretation import Interpretation


class SimilaritySearchService:
    """벡터 유사도 검색 서비스"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._embedding_service = None
        self._faiss_index = None
    
    @property
    def embedding_service(self):
        """임베딩 서비스 lazy loading"""
        if self._embedding_service is None:
            from ml.embedding import get_embedding_service
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    @property
    def faiss_index(self):
        """FAISS 인덱스 lazy loading"""
        if self._faiss_index is None:
            from ml.faiss_index import FAISSIndex
            self._faiss_index = FAISSIndex(
                index_type="case",
                dimension=768
            )
            # 기존 인덱스 로드 시도
            if not self._faiss_index.load_index():
                self._faiss_index.create_index()
        return self._faiss_index
    
    async def search_similar_cases(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        쿼리 텍스트와 유사한 판례 검색
        
        Args:
            query: 검색 쿼리 텍스트
            top_k: 반환할 최대 결과 수
            threshold: 유사도 임계값 (0~1)
        
        Returns:
            유사도 점수와 함께 판례 목록
        """
        # 인덱스가 비어있으면 빈 결과 반환
        if self.faiss_index._index is None or self.faiss_index._index.ntotal == 0:
            return []
        
        # 쿼리 임베딩
        query_embedding = self.embedding_service.encode([query])[0]
        
        # FAISS 검색
        results = self.faiss_index.search(query_embedding, top_k=top_k)
        
        # DB에서 판례 정보 조회
        similar_cases = []
        for case_id, score in results:
            if score < threshold:
                continue
            
            case = await self.session.execute(
                select(Case).where(Case.id == case_id)
            )
            case_obj = case.scalar_one_or_none()
            
            if case_obj:
                similar_cases.append({
                    "case": case_obj,
                    "similarity_score": round(score, 4),
                    "type": "case"
                })
        
        return similar_cases
    
    async def search_by_case_id(
        self,
        case_id: int,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        특정 판례와 유사한 다른 판례 검색
        """
        # 해당 판례 조회
        result = await self.session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        
        if not case:
            return []
        
        # 검색용 텍스트 생성
        search_text = case.search_text
        if not search_text:
            return []
        
        # 자기 자신 제외하고 검색
        results = await self.search_similar_cases(
            query=search_text,
            top_k=top_k + 1,  # 자기 자신 포함해서 조회
            threshold=0.3
        )
        
        # 자기 자신 제외
        return [r for r in results if r["case"].id != case_id][:top_k]
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """인덱스 통계 조회"""
        if self.faiss_index._index is None:
            return {
                "total_vectors": 0,
                "dimension": 768,
                "index_path": str(settings.faiss_index_path),
                "status": "empty"
            }
        
        return {
            "total_vectors": self.faiss_index._index.ntotal,
            "dimension": 768,
            "index_path": str(settings.faiss_index_path),
            "status": "loaded"
        }
