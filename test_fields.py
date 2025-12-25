# -*- coding: utf-8 -*-
"""필드 파싱 상태 확인"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

async def main():
    # 샘플 케이스들
    sample_ids = [607031, 608217, 612537, 612161, 608687]
    
    for case_id in sample_ids:
        print(f'\n{"="*70}')
        print(f'판례 ID: {case_id}')
        
        result = await test_html_fallback(case_id)
        
        print(f'사건번호: {result.get("사건번호", "N/A")}')
        print(f'판결유형: {result.get("판결유형", "N/A") or "(없음)"}')
        print(f'참조조문: {str(result.get("참조조문", ""))[:100] or "(없음)"}...' if result.get("참조조문") else '참조조문: (없음)')
        print(f'참조판례: {str(result.get("참조판례", ""))[:100] or "(없음)"}...' if result.get("참조판례") else '참조판례: (없음)')
        print(f'판례내용 길이: {len(result.get("판례내용", ""))}자')

if __name__ == '__main__':
    asyncio.run(main())
