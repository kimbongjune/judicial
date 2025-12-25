# -*- coding: utf-8 -*-
"""HTML 크롤링 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

async def main():
    # 테스트할 판례 ID들
    test_ids = [612537, 612161, 608687]
    
    for case_id in test_ids:
        print(f'\n{"="*60}')
        print(f'판례 ID: {case_id}')
        print('='*60)
        
        try:
            result = await test_html_fallback(case_id)
            
            print(f'사건명: {result.get("사건명", "N/A")[:50]}')
            print(f'사건번호: {result.get("사건번호", "N/A")}')
            print(f'판결요지: {result.get("판결요지", "N/A")[:100] if result.get("판결요지") else "N/A"}...')
            print(f'판례내용: {result.get("판례내용", "N/A")[:100] if result.get("판례내용") else "N/A"}...')
            
            has_content = bool(result.get("판결요지") or result.get("판례내용"))
            print(f'\n결과: {"OK" if has_content else "FAIL"} - 콘텐츠 {"있음" if has_content else "없음"}')
            
        except Exception as e:
            print(f'오류: {e}')

if __name__ == '__main__':
    asyncio.run(main())
