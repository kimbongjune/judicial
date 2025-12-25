# -*- coding: utf-8 -*-
"""사용자 제공 케이스 대량 테스트"""
import asyncio
import sys
import random
sys.path.insert(0, '.')

from etl.clients.law_api import test_html_fallback

# 사용자가 제공한 케이스 ID들 (일부 샘플링)
USER_CASE_IDS = [
    612161, 612389, 612135, 612893, 612667, 612531, 612227, 612537, 612141, 612199,
    612153, 612229, 612273, 612167, 612643, 612219, 612349, 612345, 612387, 612361,
    612515, 612267, 612445, 612547, 612367, 612621, 612541, 612991, 612979, 612989,
    612277, 612977, 612981, 612377, 612511, 612983, 612383, 608777, 612993, 612673,
    609159, 612547, 612517, 612561, 612473, 612269, 608799, 612249, 612437, 612497,
    607031, 608217, 607107, 608687, 607893, 607639, 606867, 421730, 606723, 606271,
]

async def main():
    # 30개 랜덤 샘플
    sample_ids = random.sample(USER_CASE_IDS, min(30, len(USER_CASE_IDS)))
    
    stats = {"total": 0, "full_text_ok": 0, "ref_ok": 0, "type_ok": 0, "errors": []}
    
    for i, case_id in enumerate(sample_ids):
        print(f'[{i+1}/{len(sample_ids)}] 판례 {case_id}... ', end='', flush=True)
        
        try:
            result = await test_html_fallback(case_id)
            
            stats["total"] += 1
            
            full_text = result.get("판례내용", "")
            ref_articles = result.get("참조조문", "")
            judgment_type = result.get("판결유형", "")
            
            full_ok = len(full_text) > 100
            if full_ok:
                stats["full_text_ok"] += 1
            if ref_articles:
                stats["ref_ok"] += 1
            if judgment_type:
                stats["type_ok"] += 1
            
            status = "✅" if full_ok else "❌"
            print(f'{status} full_text={len(full_text)}자, ref={bool(ref_articles)}, type={bool(judgment_type)}')
            
            if not full_ok:
                stats["errors"].append(f'{case_id}: full_text={len(full_text)}자')
                
        except Exception as e:
            print(f'❌ 오류: {str(e)[:50]}')
            stats["errors"].append(f'{case_id}: {str(e)[:50]}')
    
    print(f'\n{"="*60}')
    print(f'결과 요약 (총 {stats["total"]}건):')
    print(f'  - 판례내용: {stats["full_text_ok"]}/{stats["total"]} ({100*stats["full_text_ok"]//max(1,stats["total"])}%)')
    print(f'  - 참조조문: {stats["ref_ok"]}/{stats["total"]} ({100*stats["ref_ok"]//max(1,stats["total"])}%)')
    print(f'  - 판결유형: {stats["type_ok"]}/{stats["total"]} ({100*stats["type_ok"]//max(1,stats["total"])}%)')
    
    if stats["errors"]:
        print(f'\n실패 목록:')
        for err in stats["errors"][:10]:
            print(f'  - {err}')

if __name__ == '__main__':
    asyncio.run(main())
