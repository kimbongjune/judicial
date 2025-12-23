"""
FAISS 인덱스 관리 서비스
유사 문서 검색을 위한 벡터 인덱스
"""
import os
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import numpy as np

from app.config import settings


class FAISSIndex:
    """
    FAISS 기반 벡터 인덱스 관리
    
    지원 인덱스 타입:
    - case: 판례 인덱스
    - constitutional: 헌재결정례 인덱스
    - interpretation: 법령해석례 인덱스
    """
    
    def __init__(self, index_type: str, dimension: int = 768):
        """
        Args:
            index_type: 인덱스 타입 (case, constitutional, interpretation)
            dimension: 임베딩 차원 (기본 768)
        """
        self.index_type = index_type
        self.dimension = dimension
        self._index = None
        self._id_map: Dict[int, int] = {}  # faiss_idx -> doc_id
        self._reverse_map: Dict[int, int] = {}  # doc_id -> faiss_idx
        
        # 인덱스 파일 경로
        self.index_dir = Path(settings.faiss_index_dir)
        self.index_path = self.index_dir / f"{index_type}.index"
        self.map_path = self.index_dir / f"{index_type}.map.npy"
        
    def _ensure_dir(self):
        """인덱스 디렉토리 생성"""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_faiss(self):
        """FAISS 임포트"""
        import faiss
        return faiss
        
    def create_index(self, use_ivf: bool = False, nlist: int = 100):
        """
        새 인덱스 생성
        
        Args:
            use_ivf: IVF 인덱스 사용 여부 (대용량 데이터용)
            nlist: IVF 클러스터 수
        """
        faiss = self._load_faiss()
        
        if use_ivf:
            # IVF (Inverted File) 인덱스 - 대용량에 적합
            quantizer = faiss.IndexFlatIP(self.dimension)
            self._index = faiss.IndexIVFFlat(
                quantizer, self.dimension, nlist, faiss.METRIC_INNER_PRODUCT
            )
        else:
            # Flat 인덱스 - 정확도 최고, 소규모에 적합
            self._index = faiss.IndexFlatIP(self.dimension)
        
        self._id_map = {}
        self._reverse_map = {}
        print(f"✅ 새 FAISS 인덱스 생성: {self.index_type}")
        
    def load_index(self) -> bool:
        """
        저장된 인덱스 로드
        
        Returns:
            로드 성공 여부
        """
        if not self.index_path.exists():
            print(f"⚠️ 인덱스 파일 없음: {self.index_path}")
            return False
        
        faiss = self._load_faiss()
        
        try:
            self._index = faiss.read_index(str(self.index_path))
            
            if self.map_path.exists():
                id_array = np.load(str(self.map_path))
                self._id_map = {i: int(doc_id) for i, doc_id in enumerate(id_array)}
                self._reverse_map = {v: k for k, v in self._id_map.items()}
            
            print(f"✅ 인덱스 로드 완료: {self.index_type} ({self._index.ntotal}개)")
            return True
        except Exception as e:
            print(f"❌ 인덱스 로드 실패: {e}")
            return False
    
    def save_index(self):
        """인덱스를 파일로 저장"""
        if self._index is None:
            raise ValueError("저장할 인덱스가 없습니다")
        
        self._ensure_dir()
        faiss = self._load_faiss()
        
        faiss.write_index(self._index, str(self.index_path))
        
        # ID 매핑 저장
        id_array = np.array([self._id_map.get(i, -1) for i in range(len(self._id_map))])
        np.save(str(self.map_path), id_array)
        
        print(f"✅ 인덱스 저장 완료: {self.index_path}")
    
    def add_vectors(self, doc_ids: List[int], vectors: np.ndarray):
        """
        벡터 추가
        
        Args:
            doc_ids: 문서 ID 리스트
            vectors: 임베딩 벡터 배열 (N x dimension)
        """
        if self._index is None:
            self.create_index()
        
        # 이미 존재하는 ID 제외
        new_indices = []
        new_vectors = []
        for i, doc_id in enumerate(doc_ids):
            if doc_id not in self._reverse_map:
                new_indices.append(doc_id)
                new_vectors.append(vectors[i])
        
        if not new_vectors:
            return
        
        new_vectors = np.array(new_vectors, dtype=np.float32)
        
        # FAISS 인덱스에 추가
        start_idx = len(self._id_map)
        self._index.add(new_vectors)
        
        # ID 매핑 업데이트
        for i, doc_id in enumerate(new_indices):
            faiss_idx = start_idx + i
            self._id_map[faiss_idx] = doc_id
            self._reverse_map[doc_id] = faiss_idx
        
        print(f"➕ {len(new_vectors)}개 벡터 추가됨 (총 {self._index.ntotal}개)")
    
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        exclude_ids: Optional[List[int]] = None,
    ) -> List[Tuple[int, float]]:
        """
        유사 벡터 검색
        
        Args:
            query_vector: 쿼리 벡터 (1D 또는 2D)
            top_k: 반환할 결과 수
            exclude_ids: 제외할 문서 ID 리스트
            
        Returns:
            (문서ID, 유사도) 튜플 리스트
        """
        if self._index is None or self._index.ntotal == 0:
            return []
        
        # 쿼리 벡터 형태 조정
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        query_vector = query_vector.astype(np.float32)
        
        # 검색 수 조정 (제외 ID 고려)
        search_k = top_k + (len(exclude_ids) if exclude_ids else 0)
        search_k = min(search_k, self._index.ntotal)
        
        # 검색 실행
        scores, indices = self._index.search(query_vector, search_k)
        
        # 결과 변환 및 필터링
        results = []
        exclude_set = set(exclude_ids) if exclude_ids else set()
        
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            doc_id = self._id_map.get(int(idx))
            if doc_id is None or doc_id in exclude_set:
                continue
            results.append((doc_id, float(score)))
            if len(results) >= top_k:
                break
        
        return results
    
    @property
    def size(self) -> int:
        """인덱스 내 벡터 수"""
        return self._index.ntotal if self._index else 0


class FAISSIndexManager:
    """
    여러 FAISS 인덱스 통합 관리
    """
    
    def __init__(self):
        self._indices: Dict[str, FAISSIndex] = {}
        
    def get_index(self, index_type: str) -> FAISSIndex:
        """
        인덱스 인스턴스 반환 (없으면 생성 후 로드 시도)
        
        Args:
            index_type: case, constitutional, interpretation
            
        Returns:
            FAISSIndex 인스턴스
        """
        if index_type not in self._indices:
            index = FAISSIndex(index_type)
            index.load_index()  # 저장된 인덱스 로드 시도
            self._indices[index_type] = index
        return self._indices[index_type]
    
    def search_all(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        index_types: Optional[List[str]] = None,
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        여러 인덱스에서 통합 검색
        
        Args:
            query_vector: 쿼리 벡터
            top_k: 각 인덱스당 반환 수
            index_types: 검색할 인덱스 타입 (None이면 전체)
            
        Returns:
            인덱스타입별 검색 결과
        """
        if index_types is None:
            index_types = ["case", "constitutional", "interpretation"]
        
        results = {}
        for index_type in index_types:
            index = self.get_index(index_type)
            results[index_type] = index.search(query_vector, top_k)
        
        return results


# 싱글톤 인스턴스
_index_manager: Optional[FAISSIndexManager] = None


def get_index_manager() -> FAISSIndexManager:
    """FAISS 인덱스 매니저 싱글톤 인스턴스"""
    global _index_manager
    if _index_manager is None:
        _index_manager = FAISSIndexManager()
    return _index_manager
