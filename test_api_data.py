import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.clients.law_api import LawAPIClient

async def main():
    async with LawAPIClient() as client:
        result = await client.get_cases_list(page=1, display=5)
        print("=" * 60)
        print("실제 API 데이터 확인")
        print("=" * 60)
        
        for i, item in enumerate(result.get("items", [])[:5], 1):
            raw_case_number = item.get("사건번호", "")
            court_name = item.get("법원명", "")
            
            print(f"\n[{i}] 원본 사건번호: '{raw_case_number}'")
            print(f"    원본 법원명: '{court_name}'")
            
            parsed = LawAPIClient.parse_case_title(raw_case_number)
            print(f"    파싱 결과: {parsed}")
            
            final_case_number = parsed["case_number"] if parsed["case_number"] else raw_case_number
            print(f"    최종 case_number: '{final_case_number}'")

if __name__ == "__main__":
    asyncio.run(main())
