# -*- coding: utf-8 -*-
"""사용자 제공 CSV 케이스 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

async def main():
    # 사용자 제공 케이스들 (CSV에서 추출)
    case_ids = [
        607999, 600607, 605497, 418012, 242577, 242453, 601045, 242403,
        343839, 600147, 342569, 603691, 605697, 500975, 418132, 350488,
        351962, 608297, 351812, 348670, 607067, 607033, 608023, 348982,
    ]
    
    success_count = 0
    fail_cases = []
    
    for i, case_id in enumerate(case_ids):
        print(f'[{i+1}/{len(case_ids)}] {case_id}... ', end='', flush=True)
        
        try:
            result = await test_html_fallback(case_id)
            
            full_text = result.get("판례내용", "")
            full_ok = len(full_text) > 100
            
            if full_ok:
                success_count += 1
                print(f'✅ {len(full_text)}자')
            else:
                fail_cases.append(case_id)
                print(f'❌ {len(full_text)}자')
                
        except Exception as e:
            fail_cases.append(case_id)
            print(f'❌ 오류: {str(e)[:30]}')
    
    print(f'\n{"="*50}')
    print(f'결과: {success_count}/{len(case_ids)} 성공')
    if fail_cases:
        print(f'실패: {fail_cases}')

if __name__ == '__main__':
    asyncio.run(main())
