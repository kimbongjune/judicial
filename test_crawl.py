# -*- coding: utf-8 -*-
"""HTML 크롤링 테스트 (5초 대기 적용)"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

async def main():
    test_ids = [612537, 612161, 608687]
    
    success_count = 0
    for case_id in test_ids:
        print(f'\n{"="*60}')
        print(f'판례 ID: {case_id}')
        print('='*60)
        
        try:
            result = await test_html_fallback(case_id)
            
            print(f'사건명: {result.get("사건명", "N/A")[:50]}')
            print(f'사건번호: {result.get("사건번호", "N/A")}')
            print(f'판결요지: {str(result.get("판결요지", ""))[:80]}...' if result.get("판결요지") else "판결요지: N/A")
            print(f'판례내용: {str(result.get("판례내용", ""))[:80]}...' if result.get("판례내용") else "판례내용: N/A")
            
            has_content = bool(result.get("판결요지") or result.get("판례내용"))
            status = "OK" if has_content else "FAIL"
            print(f'\n결과: {status}')
            if has_content:
                success_count += 1
            
        except Exception as e:
            print(f'오류: {e}')
    
    print(f'\n{"="*60}')
    print(f'총 결과: {success_count}/{len(test_ids)} 성공')

if __name__ == '__main__':
    asyncio.run(main())
