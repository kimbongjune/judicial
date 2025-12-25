# -*- coding: utf-8 -*-
"""다수 케이스 샘플링 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

async def main():
    # 사용자가 제공한 케이스 중 샘플링
    sample_ids = [
        607031, 608217, 612161, 612537, 608687, 607107,  # 기존 테스트
        612389, 612893, 612667, 612531, 612991, 608777,  # 추가 샘플
        609159, 613001, 612703, 606867, 421730,  # 다양한 ID
    ]
    
    stats = {"total": 0, "with_full_text": 0, "with_ref_articles": 0, "with_judgment_type": 0}
    
    for case_id in sample_ids:
        print(f'\n{"="*60}')
        print(f'판례 ID: {case_id}')
        
        try:
            result = await test_html_fallback(case_id)
            
            stats["total"] += 1
            
            full_text_len = len(result.get("판례내용", ""))
            ref_articles = result.get("참조조문", "")
            judgment_type = result.get("판결유형", "")
            
            if full_text_len > 100:
                stats["with_full_text"] += 1
            if ref_articles:
                stats["with_ref_articles"] += 1
            if judgment_type:
                stats["with_judgment_type"] += 1
            
            print(f'판례내용: {full_text_len}자 {"✅" if full_text_len > 100 else "❌"}')
            print(f'참조조문: {ref_articles[:60]}... {"✅" if ref_articles else "❌"}' if ref_articles else '참조조문: (없음) ⚠️')
            print(f'판결유형: {judgment_type or "(없음)"} {"✅" if judgment_type else "⚠️"}')
            
        except Exception as e:
            print(f'오류: {e}')
    
    print(f'\n{"="*60}')
    print(f'통계 (총 {stats["total"]}건):')
    print(f'  - 판례내용 있음: {stats["with_full_text"]}/{stats["total"]} ({100*stats["with_full_text"]//stats["total"]}%)')
    print(f'  - 참조조문 있음: {stats["with_ref_articles"]}/{stats["total"]} ({100*stats["with_ref_articles"]//stats["total"]}%)')
    print(f'  - 판결유형 있음: {stats["with_judgment_type"]}/{stats["total"]} ({100*stats["with_judgment_type"]//stats["total"]}%)')

if __name__ == '__main__':
    asyncio.run(main())
