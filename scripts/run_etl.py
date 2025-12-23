#!/usr/bin/env python
"""
ETL 실행 스크립트
법제처 OpenAPI에서 데이터를 수집하여 DB에 저장
"""
import argparse
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


async def fetch_and_save_cases(client: LawAPIClient, max_pages: int = None, display: int = 100):
    """
    판례 데이터 수집 및 저장
    
    Args:
        client: API 클라이언트
        max_pages: 최대 수집 페이지 수 (None이면 모든 페이지)
        display: 페이지당 항목 수
    """
    print("\n📚 판례 데이터 수집 시작...")
    
    # 첫 페이지를 조회해서 전체 건수 확인
    first_result = await client.get_cases_list(page=1, display=display)
    total_count = first_result.get("totalCnt", 0)
    total_pages = (total_count + display - 1) // display  # 전체 페이지 수 계산
    
    if max_pages is None:
        max_pages = total_pages
        print(f"   📊 전체 데이터: {total_count:,}건 ({total_pages:,}페이지)")
        print(f"   🎯 수집 목표: 모든 데이터 (페이지당 {display}건)")
    else:
        max_pages = min(max_pages, total_pages)
        print(f"   📊 전체 데이터: {total_count:,}건")
        print(f"   🎯 수집 목표: {max_pages}페이지 (페이지당 {display}건, 최대 {max_pages * display:,}건)")
    
    total_saved = 0
    total_errors = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            progress_text = f"모든 페이지" if max_pages == total_pages else f"{max_pages}"
            print(f"  📄 페이지 {page}/{progress_text} 처리 중... (전체 진행률: {total_saved}/{total_count:,}건, {total_saved/max(total_count, 1)*100:.1f}%)")
            page_success = 0
            page_errors = 0
            
            try:
                if page == 1:
                    # 첫 페이지는 이미 조회했음
                    result = first_result
                else:
                    result = await client.get_cases_list(page=page, display=display)
                
                if not result.get("items"):
                    print(f"    ℹ️  더 이상 데이터 없음")
                    break
                
                total_items = len(result["items"])
                print(f"    📋 {total_items}건 발견됨")
                
                for idx, item in enumerate(result["items"], 1):
                    # 상세 조회
                    serial_no = int(item.get("판례일련번호", 0))
                    if serial_no <= 0:
                        continue
                    
                    try:
                        print(f"\r    ⏳ 처리 중... ({total_saved + 1}/{total_count:,}건)", end="", flush=True)
                        
                        detail = await client.get_case_detail(serial_no)
                        
                        # UPSERT (있으면 업데이트, 없으면 삽입)
                        case_data = {
                            "case_serial_number": serial_no,
                            "case_number": item.get("사건번호", ""),
                            "case_type_code": item.get("사건종류코드"),
                            "case_type_name": item.get("사건종류명"),
                            "court_name": item.get("법원명") or "알 수 없음",  # null/빈문자열 모두 처리
                            "court_type_code": item.get("법원종류코드"),
                            "judgment_type": item.get("선고"),
                            "case_name": item.get("사건명") or "제목 없음",  # null/빈문자열 모두 처리
                            "decision_type": detail.get("판결유형"),
                            "summary": detail.get("판시사항"),
                            "gist": detail.get("판결요지"),
                            "reference_provisions": detail.get("참조조문"),
                            "reference_cases": detail.get("참조판례"),
                            "full_text": detail.get("판례내용"),
                        }
                        
                        # 선고일자 파싱
                        if item.get("선고일자"):
                            try:
                                case_data["judgment_date"] = datetime.strptime(
                                    item["선고일자"], "%Y.%m.%d"
                                ).date()
                            except:
                                pass
                        
                        # 기존 데이터 확인
                        existing = await session.execute(
                            select(Case).where(Case.case_serial_number == serial_no)
                        )
                        existing_case = existing.scalar_one_or_none()
                        
                        if existing_case:
                            for key, value in case_data.items():
                                if hasattr(existing_case, key):
                                    setattr(existing_case, key, value)
                        else:
                            session.add(Case(**case_data))
                        
                        total_saved += 1
                        page_success += 1
                        
                    except Exception as e:
                        total_errors += 1
                        page_errors += 1
                        print(f"\r    ❌ 판례 {serial_no} 처리 실패: {str(e)[:100]}")
                        continue
                    
                    # API 요청 간격 조절
                    await asyncio.sleep(0.1)
                
                print(f"\r    ✅ 페이지 완료: 성공 {page_success}건, 실패 {page_errors}건" + " " * 20)
                await session.commit()
                
            except Exception as e:
                print(f"    ❌ 페이지 {page} 수집 실패: {str(e)[:100]}")
                continue
    
    print(f"\n🎯 판례 수집 완료")
    print(f"   ✅ 총 성공: {total_saved:,}건")
    print(f"   ❌ 총 실패: {total_errors:,}건")
    print(f"   📊 진행률: {total_saved}/{total_count:,}건 ({total_saved/max(total_count, 1)*100:.1f}%)")
    return total_saved


async def fetch_and_save_constitutional(client: LawAPIClient, max_pages: int = None, display: int = 100):
    """
    헌재결정례 데이터 수집 및 저장
    """
    print("\n⚖️ 헌재결정례 데이터 수집 시작...")
    
    # 첫 페이지를 조회해서 전체 건수 확인
    first_result = await client.get_constitutional_list(page=1, display=display)
    total_count = first_result.get("totalCnt", 0)
    total_pages = (total_count + display - 1) // display
    
    if max_pages is None:
        max_pages = total_pages
        print(f"   📊 전체 데이터: {total_count:,}건 ({total_pages:,}페이지)")
        print(f"   🎯 수집 목표: 모든 데이터 (페이지당 {display}건)")
    else:
        max_pages = min(max_pages, total_pages)
        print(f"   📊 전체 데이터: {total_count:,}건")
        print(f"   🎯 수집 목표: {max_pages}페이지 (페이지당 {display}건, 최대 {max_pages * display:,}건)")
    
    total_saved = 0
    total_errors = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            progress_text = f"모든 페이지" if max_pages == total_pages else f"{max_pages}"
            print(f"  📄 페이지 {page}/{progress_text} 처리 중... (전체 진행률: {total_saved}/{total_count:,}건, {total_saved/max(total_count, 1)*100:.1f}%)")
            page_success = 0
            page_errors = 0
            
            try:
                if page == 1:
                    # 첫 페이지는 이미 조회했음
                    result = first_result
                else:
                    result = await client.get_constitutional_list(page=page, display=display)
                
                if not result.get("items"):
                    print(f"    ℹ️  더 이상 데이터 없음")
                    break
                
                total_items = len(result["items"])
                print(f"    📋 {total_items}건 발견됨")
                
                for idx, item in enumerate(result["items"], 1):
                    serial_no = int(item.get("결정례일련번호", 0))
                    if serial_no <= 0:
                        continue
                    
                    try:
                        print(f"\r    ⏳ 처리 중... ({total_saved + 1}/{total_count:,}건)", end="", flush=True)
                        
                        detail = await client.get_constitutional_detail(serial_no)
                        
                        decision_data = {
                            "decision_serial_number": serial_no,
                            "case_number": item.get("사건번호", ""),
                            "case_type_code": item.get("사건종류코드"),
                            "case_type_name": item.get("사건종류명"),
                            "case_name": item.get("사건명") or "제목 없음",  # null/빈문자열 모두 처리
                            "decision_result": detail.get("판례결과"),
                            "ruling": detail.get("주문"),
                            "reasoning": detail.get("이유"),
                            "summary": detail.get("결정요지"),
                            "reference_provisions": detail.get("참조조문"),
                            "reference_cases": detail.get("참조판례"),
                            "full_text": detail.get("결정문"),
                        }
                        
                        if item.get("선고일"):
                            try:
                                decision_data["decision_date"] = datetime.strptime(
                                    item["선고일"], "%Y.%m.%d"
                                ).date()
                            except:
                                pass
                        
                        existing = await session.execute(
                            select(ConstitutionalDecision).where(
                                ConstitutionalDecision.decision_serial_number == serial_no
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
                        page_success += 1
                        
                    except Exception as e:
                        total_errors += 1
                        page_errors += 1
                        print(f"\r    ❌ 결정례 {serial_no} 처리 실패: {str(e)[:100]}")
                        continue
                    
                    await asyncio.sleep(0.1)
                
                print(f"\r    ✅ 페이지 완료: 성공 {page_success}건, 실패 {page_errors}건" + " " * 20)
                await session.commit()
                page += 1
                
            except Exception as e:
                print(f"    ❌ 페이지 {page} 수집 실패: {str(e)[:100]}")
                page += 1
                continue
    
    print(f"\n🎯 헌재결정례 수집 완료")
    print(f"   ✅ 총 성공: {total_saved:,}건")
    print(f"   ❌ 총 실패: {total_errors:,}건")
    print(f"   📊 진행률: {total_saved}/{total_count:,}건 ({total_saved/max(total_count, 1)*100:.1f}%)")
    return total_saved


async def fetch_and_save_interpretations(client: LawAPIClient, max_pages: int = None, display: int = 100):
    """
    법령해석례 데이터 수집 및 저장
    """
    print("\n📜 법령해석례 데이터 수집 시작...")
    
    # 첫 페이지를 조회해서 전체 건수 확인
    first_result = await client.get_interpretations_list(page=1, display=display)
    total_count = first_result.get("totalCnt", 0)
    total_pages = (total_count + display - 1) // display
    
    if max_pages is None:
        max_pages = total_pages
        print(f"   📊 전체 데이터: {total_count:,}건 ({total_pages:,}페이지)")
        print(f"   🎯 수집 목표: 모든 데이터 (페이지당 {display}건)")
    else:
        max_pages = min(max_pages, total_pages)
        print(f"   📊 전체 데이터: {total_count:,}건")
        print(f"   🎯 수집 목표: {max_pages}페이지 (페이지당 {display}건, 최대 {max_pages * display:,}건)")
    
    total_saved = 0
    total_errors = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            progress_text = f"모든 페이지" if max_pages == total_pages else f"{max_pages}"
            print(f"  📄 페이지 {page}/{progress_text} 처리 중... (전체 진행률: {total_saved}/{total_count:,}건, {total_saved/max(total_count, 1)*100:.1f}%)")
            page_success = 0
            page_errors = 0
            
            try:
                if page == 1:
                    # 첫 페이지는 이미 조회했음
                    result = first_result
                else:
                    result = await client.get_interpretations_list(page=page, display=display)
                
                if not result.get("items"):
                    print(f"    ℹ️  더 이상 데이터 없음")
                    break
                
                total_items = len(result["items"])
                print(f"    📋 {total_items}건 발견됨")
                
                for idx, item in enumerate(result["items"], 1):
                    serial_no = int(item.get("법령해석례일련번호", 0))
                    if serial_no <= 0:
                        continue
                    
                    try:
                        print(f"\r    ⏳ 처리 중... ({total_saved + 1}/{total_count:,}건)", end="", flush=True)
                        
                        detail = await client.get_interpretation_detail(serial_no)
                        
                        interp_data = {
                            "interpretation_serial_number": serial_no,
                            "agenda_number": item.get("안건번호", ""),
                            "field": item.get("분야"),
                            "law_type": item.get("법령구분명"),
                            "agenda_name": item.get("안건명") or "제목 없음",
                            "question_summary": detail.get("질의요지"),
                            "answer": detail.get("회답"),
                            "reasoning": detail.get("이유"),
                            "reference_provisions": detail.get("참조조문"),
                            "reference_cases": detail.get("참조판례"),
                            "remarks": detail.get("비고"),
                        }
                        
                        if item.get("회신일자"):
                            try:
                                interp_data["reply_date"] = datetime.strptime(
                                    item["회신일자"], "%Y.%m.%d"
                                ).date()
                            except:
                                pass
                        
                        existing = await session.execute(
                            select(Interpretation).where(
                                Interpretation.interpretation_serial_number == serial_no
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
                        page_success += 1
                        
                    except Exception as e:
                        total_errors += 1
                        page_errors += 1
                        print(f"\r    ❌ 해석례 {serial_no} 처리 실패: {str(e)[:100]}")
                        continue
                    
                    await asyncio.sleep(0.1)
                
                print(f"\r    ✅ 페이지 완료: 성공 {page_success}건, 실패 {page_errors}건" + " " * 20)
                await session.commit()
                
            except Exception as e:
                print(f"    ❌ 페이지 {page} 수집 실패: {str(e)[:100]}")
                continue
    
    print(f"\n🎯 법령해석례 수집 완료")
    print(f"   ✅ 총 성공: {total_saved:,}건")
    print(f"   ❌ 총 실패: {total_errors:,}건")
    print(f"   📊 진행률: {total_saved}/{total_count:,}건 ({total_saved/max(total_count, 1)*100:.1f}%)")
    return total_saved


async def main():
    """ETL 메인 실행"""
    parser = argparse.ArgumentParser(description='법제처 데이터 ETL')
    parser.add_argument('--target', choices=['prec', 'detc', 'expc', 'all'], 
                       default='all', help='수집 대상 (prec:판례, detc:헌재결정례, expc:법령해석례, all:전체)')
    parser.add_argument('--limit', type=int, default=None, 
                       help='수집할 최대 페이지 수 (기본값: 모든 데이터)')
    parser.add_argument('--display', type=int, default=100,
                       help='페이지당 항목 수')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 법률 데이터 ETL 시작")
    print(f"   시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   대상: {args.target}")
    print(f"   최대 페이지: {'모든 데이터' if args.limit is None else f'{args.limit}페이지'}")
    print(f"   페이지당: {args.display}건")
    print("=" * 60)
    
    cases_count = 0
    constitutional_count = 0
    interpretations_count = 0
    
    async with LawAPIClient() as client:
        if args.target == 'prec' or args.target == 'all':
            cases_count = await fetch_and_save_cases(client, args.limit, args.display)
        
        if args.target == 'detc' or args.target == 'all':
            constitutional_count = await fetch_and_save_constitutional(client, args.limit, args.display)
        
        if args.target == 'expc' or args.target == 'all':
            interpretations_count = await fetch_and_save_interpretations(client, args.limit, args.display)
    
    print("\n" + "=" * 60)
    print("✅ ETL 완료!")
    print(f"   - 판례: {cases_count}건")
    print(f"   - 헌재결정례: {constitutional_count}건")
    print(f"   - 법령해석례: {interpretations_count}건")
    print(f"   종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
