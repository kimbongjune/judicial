"""
임베딩 서비스 - Sentence Transformers 기반
한국어 법률 문서 임베딩 생성
"""
import os
from typing import List, Optional, Union
import numpy as np

from app.config import settings


class EmbeddingService:
    """
    Sentence Transformers 기반 임베딩 서비스
    
    사용 모델: jhgan/ko-sroberta-multitask (768차원)
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Args:
            model_name: 사용할 모델명 (미지정시 설정에서 로드)
        """
        self.model_name = model_name or settings.embedding_model
        self._model = None
        
    def _load_model(self):
        """모델 로드 (lazy loading)"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"🔄 임베딩 모델 로딩 중: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            print(f"✅ 임베딩 모델 로드 완료")
        return self._model
    
    @property
    def model(self):
        """모델 프로퍼티 (lazy loading)"""
        return self._load_model()
    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress_bar: bool = False,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        텍스트를 임베딩 벡터로 변환
        
        Args:
            texts: 단일 텍스트 또는 텍스트 리스트
            batch_size: 배치 크기
            show_progress_bar: 진행률 표시 여부
            normalize: L2 정규화 여부
            
        Returns:
            임베딩 벡터 (단일 텍스트: 1D, 다중 텍스트: 2D)
        """
        if isinstance(texts, str):
            texts = [texts]
            single = True
        else:
            single = False
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            normalize_embeddings=normalize,
        )
        
        if single:
            return embeddings[0]
        return embeddings
    
    def encode_case(self, case: dict) -> np.ndarray:
        """
        판례 데이터를 임베딩으로 변환
        
        Args:
            case: 판례 딕셔너리 (case_name, summary, gist 등)
            
        Returns:
            임베딩 벡터
        """
        parts = []
        
        if case.get("case_name"):
            parts.append(case["case_name"])
        if case.get("summary"):
            parts.append(case["summary"])
        if case.get("gist"):
            parts.append(case["gist"])
        
        text = " ".join(parts)
        if not text.strip():
            # 빈 텍스트 처리
            return np.zeros(768, dtype=np.float32)
        
        return self.encode(text)
    
    def encode_constitutional(self, decision: dict) -> np.ndarray:
        """
        헌재결정례 데이터를 임베딩으로 변환
        
        Args:
            decision: 결정례 딕셔너리
            
        Returns:
            임베딩 벡터
        """
        parts = []
        
        if decision.get("case_name"):
            parts.append(decision["case_name"])
        if decision.get("summary"):
            parts.append(decision["summary"])
        if decision.get("ruling"):
            parts.append(decision["ruling"])
        
        text = " ".join(parts)
        if not text.strip():
            return np.zeros(768, dtype=np.float32)
        
        return self.encode(text)
    
    def encode_interpretation(self, interpretation: dict) -> np.ndarray:
        """
        법령해석례 데이터를 임베딩으로 변환
        
        Args:
            interpretation: 해석례 딕셔너리
            
        Returns:
            임베딩 벡터
        """
        parts = []
        
        if interpretation.get("agenda_name"):
            parts.append(interpretation["agenda_name"])
        if interpretation.get("question_summary"):
            parts.append(interpretation["question_summary"])
        if interpretation.get("answer"):
            parts.append(interpretation["answer"])
        
        text = " ".join(parts)
        if not text.strip():
            return np.zeros(768, dtype=np.float32)
        
        return self.encode(text)


# 싱글톤 인스턴스
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """임베딩 서비스 싱글톤 인스턴스 반환"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
