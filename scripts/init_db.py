#!/usr/bin/env python
"""
데이터베이스 초기화 스크립트
테이블 생성 및 초기 설정
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db, drop_db, engine
from app.models import Case, ConstitutionalDecision, Interpretation


async def main():
    """데이터베이스 초기화"""
    print("=" * 50)
    print("📦 데이터베이스 초기화")
    print("=" * 50)
    
    # 기존 테이블 삭제 여부 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        print("\n⚠️ 기존 테이블을 삭제합니다...")
        await drop_db()
        print("✅ 기존 테이블 삭제 완료")
    
    # 테이블 생성
    print("\n🔨 테이블 생성 중...")
    await init_db()
    
    print("\n✅ 데이터베이스 초기화 완료!")
    print("\n생성된 테이블:")
    print("  - cases (판례)")
    print("  - constitutional_decisions (헌재결정례)")
    print("  - interpretations (법령해석례)")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
