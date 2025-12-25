# -*- coding: utf-8 -*-
"""XML vs HTML 비교 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import LawAPIClient

async def main():
    case_ids = [607999, 605497, 418012]
    
    async with LawAPIClient() as client:
        for case_id in case_ids:
            print(f'\n{"="*60}')
            print(f'판례 ID: {case_id}')
            print('='*60)
            
            # 1. XML API 직접 호출
            print('\n[1] XML API 응답:')
            try:
                xml_result = await client.get_case_detail(case_id)
                print(f'  판례내용 길이: {len(xml_result.get("판례내용", ""))}자')
                print(f'  판결요지 길이: {len(xml_result.get("판결요지", ""))}자')
                print(f'  참조조문: {xml_result.get("참조조문", "")[:50]}...' if xml_result.get("참조조문") else '  참조조문: (없음)')
                
                # 오류 메시지 확인
                result_str = str(xml_result)
                has_error = any(msg in result_str for msg in ["일치하는 판례가 없습니다", "데이터가 없습니다"])
                print(f'  오류 메시지 포함: {has_error}')
                
            except Exception as e:
                print(f'  오류: {e}')
            
            # 2. fallback으로 호출
            print('\n[2] Fallback 응답:')
            try:
                fallback_result = await client.get_case_detail_with_fallback(case_id)
                print(f'  판례내용 길이: {len(fallback_result.get("판례내용", ""))}자')
                print(f'  판결요지 길이: {len(fallback_result.get("판결요지", ""))}자')
                print(f'  참조조문: {fallback_result.get("참조조문", "")[:50]}...' if fallback_result.get("참조조문") else '  참조조문: (없음)')
                
            except Exception as e:
                print(f'  오류: {e}')

if __name__ == '__main__':
    asyncio.run(main())
