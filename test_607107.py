# -*- coding: utf-8 -*-
"""607107 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

async def main():
    case_id = 607107
    print(f'판례 ID: {case_id}')
    print('='*60)
    
    result = await test_html_fallback(case_id)
    
    print(f'사건명: {result.get("사건명", "N/A")[:60]}')
    print(f'사건번호: {result.get("사건번호", "N/A")}')
    print(f'판결요지: {str(result.get("판결요지", ""))[:100]}...' if result.get("판결요지") else "판결요지: N/A")
    print(f'판례내용 길이: {len(result.get("판례내용", ""))} 자')
    print(f'판례내용 시작: {str(result.get("판례내용", ""))[:200]}...' if result.get("판례내용") else "판례내용: N/A")
    
    has_content = bool(result.get("판례내용") and len(result.get("판례내용", "")) > 100)
    print(f'\n결과: {"OK" if has_content else "FAIL"} - 판례내용 {"있음" if has_content else "없음"}')

if __name__ == '__main__':
    asyncio.run(main())
