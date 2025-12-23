#!/usr/bin/env python
"""
ETL 실행 스크립트
법제처 OpenAPI에서 데이터를 수집하여 DB에 저장
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import async_session_maker
from app.models import Case, ConstitutionalDecision, Interpretation
from etl.clients.law_api import LawAPIClient


async def fetch_and_save_cases(client: LawAPIClient, max_pages: int = 10, display: int = 100):
    """
    판례 데이터 수집 및 저장
    
    Args:
        client: API 클라이언트
        max_pages: 최대 수집 페이지 수
        display: 페이지당 항목 수
    """
    print("\n📚 판례 데이터 수집 시작...")
    
    total_saved = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            print(f"  페이지 {page}/{max_pages} 수집 중...")
            
            try:
                result = await client.get_cases_list(page=page, display=display)
                
                if not result.get("items"):
                    print(f"  더 이상 데이터 없음 (페이지 {page})")
                    break
                
                for item in result["items"]:
                    # 상세 조회
                    serial_no = int(item.get("판례일련번호", 0))
                    if serial_no <= 0:
                        continue
                    
                    try:
                        detail = await client.get_case_detail(serial_no)
                        
                        # UPSERT (있으면 업데이트, 없으면 삽입)
                        case_data = {
                            "판례일련번호": serial_no,
                            "사건번호": item.get("사건번호", ""),
                            "사건종류코드": item.get("사건종류코드"),
                            "사건종류명": item.get("사건종류명"),
                            "법원명": item.get("법원명", ""),
                            "법원종류코드": item.get("법원종류코드"),
                            "선고": item.get("선고"),
                            "사건명": item.get("사건명", ""),
                            "판결유형": detail.get("판결유형"),
                            "판시사항": detail.get("판시사항"),
                            "판결요지": detail.get("판결요지"),
                            "참조조문": detail.get("참조조문"),
                            "참조판례": detail.get("참조판례"),
                            "판례내용": detail.get("판례내용"),
                        }
                        
                        # 선고일자 파싱
                        if item.get("선고일자"):
                            try:
                                case_data["선고일자"] = datetime.strptime(
                                    item["선고일자"], "%Y.%m.%d"
                                ).date()
                            except:
                                pass
                        
                        # 기존 데이터 확인
                        existing = await session.execute(
                            select(Case).where(Case.판례일련번호 == serial_no)
                        )
                        existing_case = existing.scalar_one_or_none()
                        
                        if existing_case:
                            for key, value in case_data.items():
                                if hasattr(existing_case, key):
                                    setattr(existing_case, key, value)
                        else:
                            session.add(Case(**case_data))
                        
                        total_saved += 1
                        
                    except Exception as e:
                        print(f"    ⚠️ 판례 {serial_no} 상세 조회 실패: {e}")
                        continue
                    
                    # API 요청 간격 조절
                    await asyncio.sleep(0.1)
                
                await session.commit()
                print(f"  ✅ 페이지 {page} 저장 완료 ({len(result['items'])}건)")
                
            except Exception as e:
                print(f"  ❌ 페이지 {page} 수집 실패: {e}")
                continue
    
    print(f"\n✅ 판례 수집 완료: 총 {total_saved}건")
    return total_saved


async def fetch_and_save_constitutional(client: LawAPIClient, max_pages: int = 10, display: int = 100):
    """
    헌재결정례 데이터 수집 및 저장
    """
    print("\n⚖️ 헌재결정례 데이터 수집 시작...")
    
    total_saved = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            print(f"  페이지 {page}/{max_pages} 수집 중...")
            
            try:
                result = await client.get_constitutional_list(page=page, display=display)
                
                if not result.get("items"):
                    print(f"  더 이상 데이터 없음 (페이지 {page})")
                    break
                
                for item in result["items"]:
                    serial_no = int(item.get("결정례일련번호", 0))
                    if serial_no <= 0:
                        continue
                    
                    try:
                        detail = await client.get_constitutional_detail(serial_no)
                        
                        decision_data = {
                            "결정례일련번호": serial_no,
                            "사건번호": item.get("사건번호", ""),
                            "사건종류코드": item.get("사건종류코드"),
                            "사건종류명": item.get("사건종류명"),
                            "사건명": item.get("사건명", ""),
                            "판례결과": detail.get("판례결과"),
                            "주문": detail.get("주문"),
                            "이유": detail.get("이유"),
                            "결정요지": detail.get("결정요지"),
                            "참조조문": detail.get("참조조문"),
                            "참조판례": detail.get("참조판례"),
                            "결정문": detail.get("결정문"),
                        }
                        
                        if item.get("선고일"):
                            try:
                                decision_data["선고일"] = datetime.strptime(
                                    item["선고일"], "%Y.%m.%d"
                                ).date()
                            except:
                                pass
                        
                        existing = await session.execute(
                            select(ConstitutionalDecision).where(
                                ConstitutionalDecision.결정례일련번호 == serial_no
                            )
                        )
                        existing_decision = existing.scalar_one_or_none()
                        
                        if existing_decision:
                            for key, value in decision_data.items():
                                if hasattr(existing_decision, key):
                                    setattr(existing_decision, key, value)
                        else:
                            session.add(ConstitutionalDecision(**decision_data))
                        
                        total_saved += 1
                        
                    except Exception as e:
                        print(f"    ⚠️ 결정례 {serial_no} 상세 조회 실패: {e}")
                        continue
                    
                    await asyncio.sleep(0.1)
                
                await session.commit()
                print(f"  ✅ 페이지 {page} 저장 완료")
                
            except Exception as e:
                print(f"  ❌ 페이지 {page} 수집 실패: {e}")
                continue
    
    print(f"\n✅ 헌재결정례 수집 완료: 총 {total_saved}건")
    return total_saved


async def fetch_and_save_interpretations(client: LawAPIClient, max_pages: int = 10, display: int = 100):
    """
    법령해석례 데이터 수집 및 저장
    """
    print("\n📜 법령해석례 데이터 수집 시작...")
    
    total_saved = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            print(f"  페이지 {page}/{max_pages} 수집 중...")
            
            try:
                result = await client.get_interpretations_list(page=page, display=display)
                
                if not result.get("items"):
                    print(f"  더 이상 데이터 없음 (페이지 {page})")
                    break
                
                for item in result["items"]:
                    serial_no = int(item.get("법령해석례일련번호", 0))
                    if serial_no <= 0:
                        continue
                    
                    try:
                        detail = await client.get_interpretation_detail(serial_no)
                        
                        interp_data = {
                            "법령해석례일련번호": serial_no,
                            "안건번호": item.get("안건번호", ""),
                            "분야": item.get("분야"),
                            "법령구분명": item.get("법령구분명"),
                            "안건명": item.get("안건명", ""),
                            "질의요지": detail.get("질의요지"),
                            "회답": detail.get("회답"),
                            "이유": detail.get("이유"),
                            "참조조문": detail.get("참조조문"),
                            "참조판례": detail.get("참조판례"),
                            "비고": detail.get("비고"),
                        }
                        
                        if item.get("회신일자"):
                            try:
                                interp_data["회신일자"] = datetime.strptime(
                                    item["회신일자"], "%Y.%m.%d"
                                ).date()
                            except:
                                pass
                        
                        existing = await session.execute(
                            select(Interpretation).where(
                                Interpretation.법령해석례일련번호 == serial_no
                            )
                        )
                        existing_interp = existing.scalar_one_or_none()
                        
                        if existing_interp:
                            for key, value in interp_data.items():
                                if hasattr(existing_interp, key):
                                    setattr(existing_interp, key, value)
                        else:
                            session.add(Interpretation(**interp_data))
                        
                        total_saved += 1
                        
                    except Exception as e:
                        print(f"    ⚠️ 해석례 {serial_no} 상세 조회 실패: {e}")
                        continue
                    
                    await asyncio.sleep(0.1)
                
                await session.commit()
                print(f"  ✅ 페이지 {page} 저장 완료")
                
            except Exception as e:
                print(f"  ❌ 페이지 {page} 수집 실패: {e}")
                continue
    
    print(f"\n✅ 법령해석례 수집 완료: 총 {total_saved}건")
    return total_saved


async def main():
    """ETL 메인 실행"""
    print("=" * 60)
    print("🚀 법률 데이터 ETL 시작")
    print(f"   시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 수집 설정 (환경에 따라 조절)
    max_pages = 5  # 테스트용: 5페이지
    display = 20   # 페이지당 20건
    
    if len(sys.argv) > 1:
        try:
            max_pages = int(sys.argv[1])
        except:
            pass
    
    print(f"\n📋 수집 설정: 최대 {max_pages} 페이지, 페이지당 {display}건")
    
    async with LawAPIClient() as client:
        # 판례 수집
        cases_count = await fetch_and_save_cases(client, max_pages, display)
        
        # 헌재결정례 수집
        constitutional_count = await fetch_and_save_constitutional(client, max_pages, display)
        
        # 법령해석례 수집
        interpretations_count = await fetch_and_save_interpretations(client, max_pages, display)
    
    print("\n" + "=" * 60)
    print("✅ ETL 완료!")
    print(f"   - 판례: {cases_count}건")
    print(f"   - 헌재결정례: {constitutional_count}건")
    print(f"   - 법령해석례: {interpretations_count}건")
    print(f"   종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
