# -*- coding: utf-8 -*-
"""608687 디버그 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import LawAPIClient

async def main():
    case_id = 608687
    
    async with LawAPIClient() as client:
        # Selenium으로 직접 크롤링
        url = f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={case_id}&mode=0"
        print(f"URL: {url}")
        result = await client._fetch_with_selenium(url, case_id)
        
        print(f"\n=== 결과 ===")
        for k, v in result.items():
            if v:
                val = str(v)[:200] if len(str(v)) > 200 else v
                print(f"{k}: {val}")

if __name__ == '__main__':
    asyncio.run(main())
