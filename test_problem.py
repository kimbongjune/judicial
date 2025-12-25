# -*- coding: utf-8 -*-
"""문제 케이스 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

async def main():
    problem_ids = [607999, 605497, 418012, 342569, 603691, 605697, 500975, 346328]
    
    for case_id in problem_ids:
        print(f'\n{"="*60}')
        print(f'판례 ID: {case_id}')
        
        try:
            result = await test_html_fallback(case_id)
            
            full_text = result.get("판례내용", "")
            ref_articles = result.get("참조조문", "")
            judgment_type = result.get("판결유형", "")
            case_number = result.get("사건번호", "")
            
            print(f'사건번호: {case_number}')
            print(f'판결유형: {judgment_type or "(없음)"}')
            print(f'참조조문: {ref_articles[:60]}...' if ref_articles else '참조조문: (없음)')
            print(f'판례내용: {len(full_text)}자 {"✅" if len(full_text) > 100 else "❌"}')
            if len(full_text) > 0:
                print(f'내용 시작: {full_text[:100]}...')
            
        except Exception as e:
            print(f'오류: {e}')

if __name__ == '__main__':
    asyncio.run(main())
