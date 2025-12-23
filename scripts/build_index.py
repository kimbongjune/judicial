#!/usr/bin/env python
"""
FAISS 인덱스 빌드 스크립트
DB의 문서 데이터로 벡터 인덱스 생성
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sqlalchemy import select, func

from app.database import async_session_maker
from app.models import Case, ConstitutionalDecision, Interpretation
from ml.embedding import get_embedding_service
from ml.faiss_index import FAISSIndex


async def build_case_index(batch_size: int = 100):
    """
    판례 FAISS 인덱스 빌드
    """
    print("\n📚 판례 인덱스 빌드 시작...")
    
    embedding_service = get_embedding_service()
    index = FAISSIndex("case")
    index.create_index()
    
    async with async_session_maker() as session:
        # 총 개수 조회
        count_result = await session.execute(select(func.count(Case.id)))
        total_count = count_result.scalar()
        print(f"   총 {total_count}건의 판례")
        
        # 배치 처리
        offset = 0
        processed = 0
        
        while offset < total_count:
            result = await session.execute(
                select(Case).offset(offset).limit(batch_size)
            )
            cases = result.scalars().all()
            
            if not cases:
                break
            
            # 임베딩 생성
            doc_ids = []
            texts = []
            
            for case in cases:
                search_text = case.search_text
                if search_text.strip():
                    doc_ids.append(case.id)
                    texts.append(search_text)
            
            if texts:
                embeddings = embedding_service.encode(texts, show_progress_bar=False)
                index.add_vectors(doc_ids, embeddings)
            
            processed += len(cases)
            print(f"   진행: {processed}/{total_count} ({processed/total_count*100:.1f}%)")
            
            offset += batch_size
    
    # 인덱스 저장
    index.save_index()
    print(f"✅ 판례 인덱스 빌드 완료: {index.size}개")
    return index.size


async def build_constitutional_index(batch_size: int = 100):
    """
    헌재결정례 FAISS 인덱스 빌드
    """
    print("\n⚖️ 헌재결정례 인덱스 빌드 시작...")
    
    embedding_service = get_embedding_service()
    index = FAISSIndex("constitutional")
    index.create_index()
    
    async with async_session_maker() as session:
        count_result = await session.execute(select(func.count(ConstitutionalDecision.id)))
        total_count = count_result.scalar()
        print(f"   총 {total_count}건의 결정례")
        
        offset = 0
        processed = 0
        
        while offset < total_count:
            result = await session.execute(
                select(ConstitutionalDecision).offset(offset).limit(batch_size)
            )
            decisions = result.scalars().all()
            
            if not decisions:
                break
            
            doc_ids = []
            texts = []
            
            for decision in decisions:
                search_text = decision.search_text
                if search_text.strip():
                    doc_ids.append(decision.id)
                    texts.append(search_text)
            
            if texts:
                embeddings = embedding_service.encode(texts, show_progress_bar=False)
                index.add_vectors(doc_ids, embeddings)
            
            processed += len(decisions)
            print(f"   진행: {processed}/{total_count} ({processed/total_count*100:.1f}%)")
            
            offset += batch_size
    
    index.save_index()
    print(f"✅ 헌재결정례 인덱스 빌드 완료: {index.size}개")
    return index.size


async def build_interpretation_index(batch_size: int = 100):
    """
    법령해석례 FAISS 인덱스 빌드
    """
    print("\n📜 법령해석례 인덱스 빌드 시작...")
    
    embedding_service = get_embedding_service()
    index = FAISSIndex("interpretation")
    index.create_index()
    
    async with async_session_maker() as session:
        count_result = await session.execute(select(func.count(Interpretation.id)))
        total_count = count_result.scalar()
        print(f"   총 {total_count}건의 해석례")
        
        offset = 0
        processed = 0
        
        while offset < total_count:
            result = await session.execute(
                select(Interpretation).offset(offset).limit(batch_size)
            )
            interpretations = result.scalars().all()
            
            if not interpretations:
                break
            
            doc_ids = []
            texts = []
            
            for interp in interpretations:
                search_text = interp.search_text
                if search_text.strip():
                    doc_ids.append(interp.id)
                    texts.append(search_text)
            
            if texts:
                embeddings = embedding_service.encode(texts, show_progress_bar=False)
                index.add_vectors(doc_ids, embeddings)
            
            processed += len(interpretations)
            print(f"   진행: {processed}/{total_count} ({processed/total_count*100:.1f}%)")
            
            offset += batch_size
    
    index.save_index()
    print(f"✅ 법령해석례 인덱스 빌드 완료: {index.size}개")
    return index.size


async def main():
    """인덱스 빌드 메인"""
    print("=" * 60)
    print("🔨 FAISS 인덱스 빌드 시작")
    print(f"   시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 인덱스 빌드
    case_count = await build_case_index()
    constitutional_count = await build_constitutional_index()
    interpretation_count = await build_interpretation_index()
    
    print("\n" + "=" * 60)
    print("✅ 인덱스 빌드 완료!")
    print(f"   - 판례 인덱스: {case_count}개")
    print(f"   - 헌재결정례 인덱스: {constitutional_count}개")
    print(f"   - 법령해석례 인덱스: {interpretation_count}개")
    print(f"   종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
