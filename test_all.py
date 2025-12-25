# -*- coding: utf-8 -*-
"""전체 크롤링 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

async def main():
    test_ids = [612537, 612161, 608687, 607107]
    
    success_count = 0
    for case_id in test_ids:
        print(f'\n{"="*60}')
        print(f'판례 ID: {case_id}')
        
        result = await test_html_fallback(case_id)
        
        case_name = result.get("사건명", "N/A")[:50]
        case_number = result.get("사건번호", "N/A")
        full_text_len = len(result.get("판례내용", ""))
        
        has_content = full_text_len > 100
        status = "OK" if has_content else "FAIL"
        
        print(f'사건명: {case_name}')
        print(f'사건번호: {case_number}')
        print(f'판례내용: {full_text_len}자')
        print(f'결과: {status}')
        
        if has_content:
            success_count += 1
    
    print(f'\n{"="*60}')
    print(f'총 결과: {success_count}/{len(test_ids)} 성공')

if __name__ == '__main__':
    asyncio.run(main())
