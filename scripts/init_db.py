#!/usr/bin/env python
"""
데이터베이스 초기화 스크립트
테이블 생성 및 초기화
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, Base, init_db, drop_db
from app.models.case import Case
from app.models.constitutional import ConstitutionalDecision
from app.models.interpretation import Interpretation


async def main():
    """데이터베이스 초기화 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='데이터베이스 초기화')
    parser.add_argument('--drop', action='store_true', 
                       help='기존 테이블 삭제 후 재생성')
    parser.add_argument('--force', action='store_true',
                       help='확인 없이 실행')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📦 데이터베이스 초기화")
    print("=" * 60)
    
    if args.drop:
        if not args.force:
            confirm = input("⚠️  모든 테이블과 데이터가 삭제됩니다. 계속하시겠습니까? (y/N): ")
            if confirm.lower() != 'y':
                print("❌ 취소되었습니다.")
                return
        
        print("\n🗑️  기존 테이블 삭제 중...")
        await drop_db()
        print("   ✅ 테이블 삭제 완료")
    
    print("\n📋 테이블 생성 중...")
    
    # 모델들을 import해서 Base.metadata에 등록되도록 함
    print(f"   - Case (판례)")
    print(f"   - ConstitutionalDecision (헌재결정례)")
    print(f"   - Interpretation (법령해석례)")
    
    await init_db()
    
    print("\n✅ 데이터베이스 초기화 완료!")
    print("=" * 60)
    
    # 테이블 확인
    async with engine.connect() as conn:
        from sqlalchemy import text, inspect
        
        def get_tables(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        
        tables = await conn.run_sync(get_tables)
        
        print("\n📊 생성된 테이블 목록:")
        for table in tables:
            print(f"   - {table}")


if __name__ == "__main__":
    asyncio.run(main())
