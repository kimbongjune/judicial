#!/usr/bin/env python
"""
ETL 실행 스크립트
법제처 OpenAPI에서 데이터를 수집하여 DB에 저장
+ FAISS 벡터 인덱스 동시 빌드 (수집하면서 바로 벡터화)
"""
import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session_maker
from app.models import Case, ConstitutionalDecision, Interpretation
from app.models.law import Law, LawArticle, LawTerm, LawHistory
from etl.clients.law_api import LawAPIClient
from ml.embedding import get_embedding_service
from ml.faiss_index import FAISSIndex


async def fetch_and_save_cases(client: LawAPIClient, max_pages: int = None, display: int = 100, 
                               embedding_service=None, faiss_index=None, concurrency: int = 5):
    """
    판례 데이터 수집 및 저장 + 벡터화
    
    Args:
        client: API 클라이언트
        max_pages: 최대 수집 페이지 수 (None이면 모든 페이지)
        display: 페이지당 항목 수
        embedding_service: 임베딩 서비스 (None이면 벡터화 스킵)
        faiss_index: FAISS 인덱스 (None이면 벡터화 스킵)
    """
    print("\n📚 판례 데이터 수집 시작...")
    print(f"   ⚡ 병렬 처리: 동시 {concurrency}건")
    do_vectorize = embedding_service is not None and faiss_index is not None
    if do_vectorize:
        print("   🧠 벡터화 모드: 수집하면서 바로 FAISS 인덱스 빌드")
    
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
    total_vectorized = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            progress_text = f"모든 페이지" if max_pages == total_pages else f"{max_pages}"
            print(f"  📄 페이지 {page}/{progress_text} 처리 중... (전체 진행률: {total_saved}/{total_count:,}건, {total_saved/max(total_count, 1)*100:.1f}%)")
            page_success = 0
            page_errors = 0
            
            # 배치 벡터화용 버퍼
            batch_ids = []
            batch_texts = []
            
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
                print(f"    📋 {total_items}건 발견됨, 병렬 처리 시작...")
                
                # 병렬 처리용 Semaphore
                semaphore = asyncio.Semaphore(concurrency)
                
                async def process_single_case(item):
                    """단일 판례 처리 (병렬 실행됨)"""
                    async with semaphore:
                        serial_no = int(item.get("판례일련번호", 0))
                        if serial_no <= 0:
                            return None
                        
                        try:
                            # XML API 시도 → 실패 시 HTML + Selenium fallback
                            detail = await client.get_case_detail_with_fallback(serial_no)
                            
                            # 사건번호에서 법원명 파싱
                            raw_case_number = item.get("사건번호", "")
                            parsed = LawAPIClient.parse_case_title(raw_case_number)
                            
                            # 법원명 결정
                            court_name = item.get("법원명") or ""
                            if not court_name and parsed["court_name"]:
                                court_name = parsed["court_name"]
                            if not court_name:
                                court_name = LawAPIClient.extract_court_from_case_number(parsed["case_number"])
                            if not court_name:
                                court_name = "알 수 없음"
                            
                            case_number = parsed["case_number"] if parsed["case_number"] else raw_case_number
                            judgment_type = item.get("선고") or detail.get("선고") or item.get("판결유형") or ""
                            
                            case_data = {
                                "case_serial_number": serial_no,
                                "case_number": case_number,
                                "case_type_code": item.get("사건종류코드"),
                                "case_type_name": item.get("사건종류명"),
                                "court_name": court_name,
                                "court_type_code": item.get("법원종류코드"),
                                "judgment_type": judgment_type,
                                "case_name": item.get("사건명") or "제목 없음",
                                "decision_type": detail.get("판결유형") or item.get("판결유형"),
                                "summary": detail.get("판시사항"),
                                "gist": detail.get("판결요지"),
                                "reference_provisions": detail.get("참조조문"),
                                "reference_cases": detail.get("참조판례"),
                                "full_text": detail.get("판례내용"),
                            }
                            
                            if item.get("선고일자"):
                                try:
                                    case_data["judgment_date"] = datetime.strptime(
                                        item["선고일자"], "%Y.%m.%d"
                                    ).date()
                                except:
                                    pass
                            
                            return {"success": True, "serial_no": serial_no, "case_data": case_data, "item": item}
                            
                        except Exception as e:
                            return {"success": False, "serial_no": serial_no, "error": str(e)[:100]}
                
                # 모든 아이템 병렬 처리
                tasks = [process_single_case(item) for item in result["items"]]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 결과 처리 (DB 저장은 순차적으로)
                for res in results:
                    if res is None:
                        continue
                    if isinstance(res, Exception):
                        total_errors += 1
                        page_errors += 1
                        continue
                    
                    if not res.get("success"):
                        total_errors += 1
                        page_errors += 1
                        print(f"\r    ❌ 판례 {res.get('serial_no')} 처리 실패: {res.get('error')}")
                        continue
                    
                    serial_no = res["serial_no"]
                    case_data = res["case_data"]
                    
                    try:
                        # DB 저장
                        existing = await session.execute(
                            select(Case).where(Case.case_serial_number == serial_no)
                        )
                        existing_case = existing.scalar_one_or_none()
                        
                        if existing_case:
                            for key, value in case_data.items():
                                if hasattr(existing_case, key):
                                    setattr(existing_case, key, value)
                            db_id = existing_case.id
                        else:
                            new_case = Case(**case_data)
                            session.add(new_case)
                            await session.flush()
                            db_id = new_case.id
                        
                        # 벡터화용 텍스트 생성
                        if do_vectorize:
                            search_text_parts = []
                            if case_data.get("case_name"):
                                search_text_parts.append(case_data["case_name"])
                            if case_data.get("summary"):
                                search_text_parts.append(case_data["summary"])
                            if case_data.get("gist"):
                                search_text_parts.append(case_data["gist"])
                            
                            search_text = " ".join(search_text_parts)
                            if search_text.strip():
                                batch_ids.append(db_id)
                                batch_texts.append(search_text)
                        
                        total_saved += 1
                        page_success += 1
                        
                    except Exception as e:
                        total_errors += 1
                        page_errors += 1
                        print(f"\r    ❌ 판례 {serial_no} DB 저장 실패: {str(e)[:100]}")
                        continue
                
                print(f"\r    ✅ 페이지 완료: 성공 {page_success}건, 실패 {page_errors}건" + " " * 20)
                await session.commit()
                
                # 배치 벡터화 (페이지 단위)
                if do_vectorize and batch_texts:
                    print(f"    🧠 벡터화 중... ({len(batch_texts)}건)")
                    embeddings = embedding_service.encode(batch_texts, show_progress_bar=False)
                    faiss_index.add_vectors(batch_ids, embeddings)
                    total_vectorized += len(batch_texts)
                    print(f"    ✅ 벡터화 완료: {len(batch_texts)}건 (누적: {total_vectorized}건)")
                
            except Exception as e:
                print(f"    ❌ 페이지 {page} 수집 실패: {str(e)[:100]}")
                continue
    
    # FAISS 인덱스 저장
    if do_vectorize:
        faiss_index.save_index()
        print(f"   💾 FAISS 인덱스 저장 완료 (총 {total_vectorized}건)")
    
    print(f"\n🎯 판례 수집 완료")
    print(f"   ✅ 총 성공: {total_saved:,}건")
    print(f"   ❌ 총 실패: {total_errors:,}건")
    if do_vectorize:
        print(f"   🧠 벡터화: {total_vectorized:,}건")
    print(f"   📊 진행률: {total_saved}/{total_count:,}건 ({total_saved/max(total_count, 1)*100:.1f}%)")
    return total_saved


async def fetch_and_save_constitutional(client: LawAPIClient, max_pages: int = None, display: int = 100,
                                        embedding_service=None, faiss_index=None, concurrency: int = 5):
    """
    헌재결정례 데이터 수집 및 저장 + 벡터화
    """
    print("\n⚖️ 헌재결정례 데이터 수집 시작...")
    print(f"   ⚡ 병렬 처리: 동시 {concurrency}건")
    do_vectorize = embedding_service is not None and faiss_index is not None
    if do_vectorize:
        print("   🧠 벡터화 모드: 수집하면서 바로 FAISS 인덱스 빌드")
    
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
    total_vectorized = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            progress_text = f"모든 페이지" if max_pages == total_pages else f"{max_pages}"
            print(f"  📄 페이지 {page}/{progress_text} 처리 중... (전체 진행률: {total_saved}/{total_count:,}건, {total_saved/max(total_count, 1)*100:.1f}%)")
            page_success = 0
            page_errors = 0
            batch_ids = []
            batch_texts = []
            
            try:
                if page == 1:
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
                            "case_name": item.get("사건명") or "제목 없음",
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
                            db_id = existing_decision.id
                        else:
                            new_decision = ConstitutionalDecision(**decision_data)
                            session.add(new_decision)
                            await session.flush()
                            db_id = new_decision.id
                        
                        # 벡터화용 텍스트 생성
                        if do_vectorize:
                            search_parts = []
                            if decision_data.get("case_name"):
                                search_parts.append(decision_data["case_name"])
                            if decision_data.get("summary"):
                                search_parts.append(decision_data["summary"])
                            search_text = " ".join(search_parts)
                            if search_text.strip():
                                batch_ids.append(db_id)
                                batch_texts.append(search_text)
                        
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
                
                # 배치 벡터화
                if do_vectorize and batch_texts:
                    print(f"    🧠 벡터화 중... ({len(batch_texts)}건)")
                    embeddings = embedding_service.encode(batch_texts, show_progress_bar=False)
                    faiss_index.add_vectors(batch_ids, embeddings)
                    total_vectorized += len(batch_texts)
                
            except Exception as e:
                print(f"    ❌ 페이지 {page} 수집 실패: {str(e)[:100]}")
                continue
    
    if do_vectorize:
        faiss_index.save_index()
        print(f"   💾 FAISS 인덱스 저장 완료 (총 {total_vectorized}건)")
    
    print(f"\n🎯 헌재결정례 수집 완료")
    print(f"   ✅ 총 성공: {total_saved:,}건")
    print(f"   ❌ 총 실패: {total_errors:,}건")
    if do_vectorize:
        print(f"   🧠 벡터화: {total_vectorized:,}건")
    print(f"   📊 진행률: {total_saved}/{total_count:,}건 ({total_saved/max(total_count, 1)*100:.1f}%)")
    return total_saved


async def fetch_and_save_interpretations(client: LawAPIClient, max_pages: int = None, display: int = 100,
                                         embedding_service=None, faiss_index=None, concurrency: int = 5):
    """
    법령해석례 데이터 수집 및 저장 + 벡터화
    """
    print("\n📜 법령해석례 데이터 수집 시작...")
    do_vectorize = embedding_service is not None and faiss_index is not None
    if do_vectorize:
        print("   🧠 벡터화 모드: 수집하면서 바로 FAISS 인덱스 빌드")
    
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
    total_vectorized = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            progress_text = f"모든 페이지" if max_pages == total_pages else f"{max_pages}"
            print(f"  📄 페이지 {page}/{progress_text} 처리 중... (전체 진행률: {total_saved}/{total_count:,}건, {total_saved/max(total_count, 1)*100:.1f}%)")
            page_success = 0
            page_errors = 0
            batch_ids = []
            batch_texts = []
            
            try:
                if page == 1:
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
                            db_id = existing_interp.id
                        else:
                            new_interp = Interpretation(**interp_data)
                            session.add(new_interp)
                            await session.flush()
                            db_id = new_interp.id
                        
                        # 벡터화용 텍스트 생성
                        if do_vectorize:
                            search_parts = []
                            if interp_data.get("agenda_name"):
                                search_parts.append(interp_data["agenda_name"])
                            if interp_data.get("question_summary"):
                                search_parts.append(interp_data["question_summary"])
                            if interp_data.get("answer"):
                                search_parts.append(interp_data["answer"])
                            search_text = " ".join(search_parts)
                            if search_text.strip():
                                batch_ids.append(db_id)
                                batch_texts.append(search_text)
                        
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
                
                # 배치 벡터화
                if do_vectorize and batch_texts:
                    print(f"    🧠 벡터화 중... ({len(batch_texts)}건)")
                    embeddings = embedding_service.encode(batch_texts, show_progress_bar=False)
                    faiss_index.add_vectors(batch_ids, embeddings)
                    total_vectorized += len(batch_texts)
                
            except Exception as e:
                print(f"    ❌ 페이지 {page} 수집 실패: {str(e)[:100]}")
                continue
    
    if do_vectorize:
        faiss_index.save_index()
        print(f"   💾 FAISS 인덱스 저장 완료 (총 {total_vectorized}건)")
    
    print(f"\n🎯 법령해석례 수집 완료")
    print(f"   ✅ 총 성공: {total_saved:,}건")
    print(f"   ❌ 총 실패: {total_errors:,}건")
    if do_vectorize:
        print(f"   🧠 벡터화: {total_vectorized:,}건")
    print(f"   📊 진행률: {total_saved}/{total_count:,}건 ({total_saved/max(total_count, 1)*100:.1f}%)")
    return total_saved


async def fetch_and_save_law_terms(client: LawAPIClient, max_pages: int = None, display: int = 100):
    """
    법령용어 데이터 수집 및 저장
    """
    print("\n📖 법령용어 데이터 수집 시작...")
    
    # 첫 페이지를 조회해서 전체 건수 확인
    first_result = await client.get_law_terms_list(page=1, display=display)
    total_count = first_result.get("totalCnt", 0)
    total_pages = (total_count + display - 1) // display
    
    if max_pages is None:
        max_pages = total_pages
        print(f"   📊 전체 데이터: {total_count:,}건 ({total_pages:,}페이지)")
    else:
        max_pages = min(max_pages, total_pages)
        print(f"   📊 전체 데이터: {total_count:,}건")
        print(f"   🎯 수집 목표: {max_pages}페이지")
    
    total_saved = 0
    total_errors = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            print(f"  📄 페이지 {page}/{max_pages} 처리 중...")
            page_success = 0
            page_errors = 0
            
            try:
                if page == 1:
                    result = first_result
                else:
                    result = await client.get_law_terms_list(page=page, display=display)
                
                if not result.get("items"):
                    print(f"    ℹ️  더 이상 데이터 없음")
                    break
                
                for item in result["items"]:
                    serial_no = int(item.get("법령용어일련번호", 0) or item.get("lsTrmSeq", 0))
                    if serial_no <= 0:
                        continue
                    
                    try:
                        # 상세 조회
                        detail = await client.get_law_term_detail(serial_no)
                        
                        term_data = {
                            "term_serial_number": serial_no,
                            "term": item.get("용어명", "") or item.get("lsTrmNm", "") or "",
                            "definition": detail.get("정의") or detail.get("용어정의") or "",
                            "example": detail.get("사용예시") or "",
                            "related_law": detail.get("관련법령") or "",
                            "related_article": detail.get("관련조문") or "",
                        }
                        
                        if not term_data["term"]:
                            continue
                        
                        # UPSERT
                        existing = await session.execute(
                            select(LawTerm).where(LawTerm.term_serial_number == serial_no)
                        )
                        existing_term = existing.scalar_one_or_none()
                        
                        if existing_term:
                            for key, value in term_data.items():
                                if hasattr(existing_term, key):
                                    setattr(existing_term, key, value)
                        else:
                            new_term = LawTerm(**term_data)
                            session.add(new_term)
                        
                        total_saved += 1
                        page_success += 1
                        
                    except Exception as e:
                        total_errors += 1
                        page_errors += 1
                        print(f"\r    ❌ 용어 {serial_no} 처리 실패: {str(e)[:100]}")
                        continue
                    
                    await asyncio.sleep(0.05)
                
                print(f"    ✅ 페이지 완료: 성공 {page_success}건, 실패 {page_errors}건")
                await session.commit()
                
            except Exception as e:
                print(f"    ❌ 페이지 {page} 수집 실패: {str(e)[:100]}")
                continue
    
    print(f"\n🎯 법령용어 수집 완료")
    print(f"   ✅ 총 성공: {total_saved:,}건")
    print(f"   ❌ 총 실패: {total_errors:,}건")
    return total_saved


async def fetch_and_save_laws(client: LawAPIClient, max_pages: int = None, display: int = 100):
    """
    법령 데이터 수집 및 저장 (연혁 포함)
    """
    print("\n📜 법령 데이터 수집 시작...")
    
    # 첫 페이지를 조회해서 전체 건수 확인
    first_result = await client.get_laws_list(page=1, display=display)
    total_count = first_result.get("totalCnt", 0)
    total_pages = (total_count + display - 1) // display
    
    if max_pages is None:
        max_pages = total_pages
        print(f"   📊 전체 데이터: {total_count:,}건 ({total_pages:,}페이지)")
    else:
        max_pages = min(max_pages, total_pages)
        print(f"   📊 전체 데이터: {total_count:,}건")
        print(f"   🎯 수집 목표: {max_pages}페이지")
    
    total_saved = 0
    total_errors = 0
    
    async with async_session_maker() as session:
        for page in range(1, max_pages + 1):
            print(f"  📄 페이지 {page}/{max_pages} 처리 중...")
            page_success = 0
            page_errors = 0
            
            try:
                if page == 1:
                    result = first_result
                else:
                    result = await client.get_laws_list(page=page, display=display)
                
                if not result.get("items"):
                    print(f"    ℹ️  더 이상 데이터 없음")
                    break
                
                for item in result["items"]:
                    serial_no = int(item.get("법령일련번호", 0) or item.get("MST", 0))
                    if serial_no <= 0:
                        continue
                    
                    try:
                        # 상세 조회
                        detail = await client.get_law_detail(serial_no)
                        
                        law_data = {
                            "law_serial_number": serial_no,
                            "law_id": item.get("법령ID") or "",
                            "law_name": item.get("법령명한글") or item.get("법령명") or "",
                            "law_name_korean": item.get("법령명한글") or "",
                            "law_name_abbreviated": item.get("법령약칭명") or "",
                            "law_type": item.get("법령구분") or "",
                            "ministry": item.get("소관부처") or "",
                            "promulgation_number": item.get("공포번호") or "",
                            "is_effective": True,
                            "purpose": detail.get("제개정이유") or "",
                        }
                        
                        # 날짜 파싱
                        if item.get("시행일자"):
                            try:
                                law_data["enforcement_date"] = datetime.strptime(
                                    item["시행일자"], "%Y%m%d"
                                ).date()
                            except:
                                pass
                        
                        if item.get("공포일자"):
                            try:
                                law_data["promulgation_date"] = datetime.strptime(
                                    item["공포일자"], "%Y%m%d"
                                ).date()
                            except:
                                pass
                        
                        if not law_data["law_name"]:
                            continue
                        
                        # UPSERT
                        existing = await session.execute(
                            select(Law).where(Law.law_serial_number == serial_no)
                        )
                        existing_law = existing.scalar_one_or_none()
                        
                        if existing_law:
                            for key, value in law_data.items():
                                if hasattr(existing_law, key):
                                    setattr(existing_law, key, value)
                            db_id = existing_law.id
                        else:
                            new_law = Law(**law_data)
                            session.add(new_law)
                            await session.flush()
                            db_id = new_law.id
                        
                        total_saved += 1
                        page_success += 1
                        
                    except Exception as e:
                        total_errors += 1
                        page_errors += 1
                        print(f"\r    ❌ 법령 {serial_no} 처리 실패: {str(e)[:100]}")
                        continue
                    
                    await asyncio.sleep(0.1)
                
                print(f"    ✅ 페이지 완료: 성공 {page_success}건, 실패 {page_errors}건")
                await session.commit()
                
            except Exception as e:
                print(f"    ❌ 페이지 {page} 수집 실패: {str(e)[:100]}")
                continue
    
    print(f"\n🎯 법령 수집 완료")
    print(f"   ✅ 총 성공: {total_saved:,}건")
    print(f"   ❌ 총 실패: {total_errors:,}건")
    return total_saved


async def main():
    """ETL 메인 실행"""
    parser = argparse.ArgumentParser(description='법제처 데이터 ETL')
    parser.add_argument('--target', choices=['prec', 'detc', 'expc', 'law', 'term', 'all'], 
                       default='all', help='수집 대상 (prec:판례, detc:헌재결정례, expc:법령해석례, law:법령, term:법령용어, all:전체)')
    parser.add_argument('--limit', type=int, default=None, 
                       help='수집할 최대 페이지 수 (기본값: 모든 데이터)')
    parser.add_argument('--display', type=int, default=100,
                       help='페이지당 항목 수')
    parser.add_argument('--no-vectorize', action='store_true',
                       help='벡터화 비활성화 (DB 저장만)')
    parser.add_argument('--concurrency', type=int, default=5,
                       help='동시 처리 개수 (기본값: 5)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 법률 데이터 ETL 시작")
    print(f"   시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   대상: {args.target}")
    print(f"   최대 페이지: {'모든 데이터' if args.limit is None else f'{args.limit}페이지'}")
    print(f"   페이지당: {args.display}건")
    print(f"   벡터화: {'비활성화' if args.no_vectorize else '활성화'}")
    print(f"   동시 처리: {args.concurrency}건")
    print("=" * 60)
    
    # 임베딩 서비스 및 FAISS 인덱스 초기화
    embedding_service = None
    case_index = None
    constitutional_index = None
    interpretation_index = None
    
    if not args.no_vectorize and args.target in ['prec', 'detc', 'expc', 'all']:
        print("\n🧠 임베딩 모델 로딩 중...")
        embedding_service = get_embedding_service()
        print("   ✅ 임베딩 모델 로드 완료")
        
        # 각 타입별 FAISS 인덱스 생성/로드
        if args.target in ['prec', 'all']:
            case_index = FAISSIndex("case")
            case_index.create_index()
            print("   ✅ 판례 FAISS 인덱스 준비 완료")
        
        if args.target in ['detc', 'all']:
            constitutional_index = FAISSIndex("constitutional")
            constitutional_index.create_index()
            print("   ✅ 헌재결정례 FAISS 인덱스 준비 완료")
        
        if args.target in ['expc', 'all']:
            interpretation_index = FAISSIndex("interpretation")
            interpretation_index.create_index()
            print("   ✅ 법령해석례 FAISS 인덱스 준비 완료")
    
    cases_count = 0
    constitutional_count = 0
    interpretations_count = 0
    laws_count = 0
    terms_count = 0
    
    async with LawAPIClient() as client:
        if args.target == 'prec' or args.target == 'all':
            cases_count = await fetch_and_save_cases(
                client, args.limit, args.display, 
                embedding_service, case_index, args.concurrency
            )
        
        if args.target == 'detc' or args.target == 'all':
            constitutional_count = await fetch_and_save_constitutional(
                client, args.limit, args.display,
                embedding_service, constitutional_index, args.concurrency
            )
        
        if args.target == 'expc' or args.target == 'all':
            interpretations_count = await fetch_and_save_interpretations(
                client, args.limit, args.display,
                embedding_service, interpretation_index, args.concurrency
            )
        
        if args.target == 'law' or args.target == 'all':
            laws_count = await fetch_and_save_laws(
                client, args.limit, args.display
            )
        
        if args.target == 'term' or args.target == 'all':
            terms_count = await fetch_and_save_law_terms(
                client, args.limit, args.display
            )
    
    print("\n" + "=" * 60)
    print("✅ ETL 완료!")
    print(f"   - 판례: {cases_count}건")
    print(f"   - 헌재결정례: {constitutional_count}건")
    print(f"   - 법령해석례: {interpretations_count}건")
    print(f"   - 법령: {laws_count}건")
    print(f"   - 법령용어: {terms_count}건")
    if not args.no_vectorize and args.target in ['prec', 'detc', 'expc', 'all']:
        print(f"   - FAISS 인덱스: 저장 완료")
    print(f"   종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
