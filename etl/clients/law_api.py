"""
법제처 OpenAPI 클라이언트
판례, 헌재결정례, 법령해석례, 법령, 법령용어 API 호출
HTML Fallback 크롤링 지원
Selenium을 통한 JS 렌더링 페이지 파싱 지원 (병렬 처리 지원)
"""
import asyncio
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from app.config import settings

# Selenium용 ThreadPoolExecutor (여러 Chrome 인스턴스 병렬 실행)
_selenium_executor: Optional[ThreadPoolExecutor] = None


def get_selenium_executor(max_workers: int = 5) -> ThreadPoolExecutor:
    """Selenium용 전역 ThreadPoolExecutor 반환"""
    global _selenium_executor
    if _selenium_executor is None or _selenium_executor._shutdown:
        _selenium_executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="selenium")
    return _selenium_executor


def shutdown_selenium_executor():
    """Selenium Executor 종료"""
    global _selenium_executor
    if _selenium_executor is not None:
        _selenium_executor.shutdown(wait=True)
        _selenium_executor = None


class LawAPIClient:
    """
    법제처 OpenAPI 비동기 클라이언트
    
    사용 예시:
        async with LawAPIClient() as client:
            cases = await client.get_cases_list(search="손해배상", page=1)
            case_detail = await client.get_case_detail(case_serial_number=12345)
    """
    
    BASE_URL = "https://www.law.go.kr/DRF"
    LSW_URL = "https://www.law.go.kr/LSW"
    
    def __init__(self, oc: Optional[str] = None):
        """
        Args:
            oc: OpenAPI 인증키 (미지정시 설정에서 로드)
        """
        self.oc = oc or settings.law_api_oc
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """async context manager 진입"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async context manager 종료"""
        if self._session:
            await self._session.close()
            self._session = None
    
    def _parse_xml(self, xml_text: str) -> Dict[str, Any]:
        """
        XML 응답을 딕셔너리로 변환
        
        Args:
            xml_text: XML 문자열
            
        Returns:
            파싱된 딕셔너리
        """
        root = ET.fromstring(xml_text)
        
        result = {
            "totalCnt": 0,
            "items": []
        }
        
        # 전체 개수 파싱
        total_cnt = root.find(".//totalCnt")
        if total_cnt is not None and total_cnt.text:
            result["totalCnt"] = int(total_cnt.text)
        
        # 목록 아이템 파싱 (prec, Detc, expc, law, lstrm 등 - 대소문자 주의!)
        for item in root.findall(".//prec") + root.findall(".//Detc") + root.findall(".//expc") + root.findall(".//law") + root.findall(".//lstrm"):
            item_dict = {}
            for child in item:
                item_dict[child.tag] = child.text
            if item_dict:
                result["items"].append(item_dict)
        
        # 단일 상세 조회 응답인 경우
        if not result["items"]:
            for child in root:
                if child.tag not in ["totalCnt", "page", "numOfRows"]:
                    result[child.tag] = child.text
        
        return result
    
    def _parse_json(self, json_text: str) -> Dict[str, Any]:
        """
        JSON 응답을 딕셔너리로 변환
        
        법제처 API JSON 응답 구조:
        - 목록 조회: {"PrecSearch": {"prec": [...], "totalCnt": "123"}}
        - 상세 조회: {"PrecService": {"사건명": "...", "판례내용": "..."}}
        
        Args:
            json_text: JSON 문자열
            
        Returns:
            파싱된 딕셔너리
        """
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 실패: {e}")
            print(f"응답 내용 (앞 500자): {json_text[:500]}")
            # XML 응답이 왔을 수 있음 - fallback
            if json_text.strip().startswith("<?xml") or json_text.strip().startswith("<"):
                print("XML 응답 감지, XML 파서로 fallback")
                return self._parse_xml(json_text)
            raise
        
        result = {
            "totalCnt": 0,
            "items": []
        }
        
        # 목록 조회 응답 (~Search 키 안에 데이터가 있음)
        # 예: PrecSearch, DetcSearch, ExpcSearch, LawSearch, LstrmSearch
        search_keys = ["PrecSearch", "DetcSearch", "ExpcSearch", "LawSearch", "LstrmSearch"]
        list_keys = ["prec", "Detc", "expc", "law", "lstrm"]
        
        for search_key in search_keys:
            if search_key in data and isinstance(data[search_key], dict):
                search_data = data[search_key]
                
                # totalCnt 파싱
                if "totalCnt" in search_data:
                    result["totalCnt"] = int(search_data["totalCnt"])
                
                # 목록 아이템 파싱
                for list_key in list_keys:
                    if list_key in search_data:
                        items = search_data[list_key]
                        if isinstance(items, dict):
                            items = [items]
                        if isinstance(items, list):
                            result["items"].extend(items)
        
        # 직접 목록 키가 있는 경우 (fallback)
        if not result["items"]:
            for key in list_keys:
                if key in data:
                    items = data[key]
                    if isinstance(items, dict):
                        items = [items]
                    if isinstance(items, list):
                        result["items"].extend(items)
            
            # totalCnt 직접 파싱
            if "totalCnt" in data:
                result["totalCnt"] = int(data["totalCnt"])
        
        # 상세 조회 응답인 경우 (~Service 키 안에 데이터가 있음)
        # 예: PrecService, DetcService, ExpcService, LawService, LstrmService
        service_keys = ["PrecService", "DetcService", "ExpcService", "LawService", "LstrmService"]
        for key in service_keys:
            if key in data and isinstance(data[key], dict):
                # Service 안의 데이터를 result에 복사
                for k, v in data[key].items():
                    result[k] = v
        
        # 상세 조회 응답인 경우 (직접 필드가 있는 경우 - fallback)
        if not result["items"] and not any(k in result for k in ["사건명", "판례내용", "판결요지"]):
            exclude_keys = ["totalCnt", "page", "numOfRows"] + search_keys + service_keys
            for key, value in data.items():
                if key not in exclude_keys:
                    result[key] = value
        
        return result
    
    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 요청 실행
        
        Args:
            endpoint: API 엔드포인트 (lawSearch.do 등)
            params: 요청 파라미터
            
        Returns:
            파싱된 응답 딕셔너리
        """
        if not self._session:
            raise RuntimeError("클라이언트가 초기화되지 않았습니다. async with 문을 사용하세요.")
        
        # 기본 파라미터 추가 (JSON으로 요청)
        params = {
            "OC": self.oc,
            "type": "JSON",
            **params
        }
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with self._session.get(url, params=params) as response:
                response.raise_for_status()
                text = await response.text()
                return self._parse_json(text)
        except aiohttp.ClientError as e:
            print(f"API 요청 실패: {e}")
            raise
    
    # ===========================================
    # 판례 API (prec)
    # ===========================================
    
    async def get_cases_list(
        self,
        search: Optional[str] = None,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        page: int = 1,
        display: int = 20,
    ) -> Dict[str, Any]:
        """
        판례 목록 조회
        
        Args:
            search: 검색어
            court: 법원명 필터
            case_type: 사건종류 필터
            page: 페이지 번호 (1부터 시작)
            display: 페이지당 표시 개수
            
        Returns:
            판례 목록 결과
        """
        params = {
            "target": "prec",
            "page": page,
            "display": display,
        }
        
        if search:
            params["query"] = search
        if court:
            params["법원명"] = court
        if case_type:
            params["사건종류명"] = case_type
            
        return await self._request("lawSearch.do", params)
    
    async def get_case_detail(self, case_serial_number: int) -> Dict[str, Any]:
        """
        판례 상세 조회
        
        Args:
            case_serial_number: 판례 고유 일련번호
            
        Returns:
            판례 상세 정보
        """
        params = {
            "target": "prec",
            "ID": case_serial_number,
        }
        return await self._request("lawService.do", params)
    
    # ===========================================
    # 헌재결정례 API (detc)
    # ===========================================
    
    async def get_constitutional_list(
        self,
        search: Optional[str] = None,
        case_type: Optional[str] = None,
        page: int = 1,
        display: int = 20,
    ) -> Dict[str, Any]:
        """
        헌재결정례 목록 조회
        
        Args:
            search: 검색어
            case_type: 사건종류 필터 (헌마, 헌바, 헌가 등)
            page: 페이지 번호
            display: 페이지당 표시 개수
            
        Returns:
            헌재결정례 목록 결과
        """
        params = {
            "target": "detc",
            "page": page,
            "display": display,
        }
        
        if search:
            params["query"] = search
        if case_type:
            params["사건종류명"] = case_type
            
        return await self._request("lawSearch.do", params)
    
    async def get_constitutional_detail(self, decision_serial_number: int) -> Dict[str, Any]:
        """
        헌재결정례 상세 조회
        
        Args:
            decision_serial_number: 결정례 고유 일련번호
            
        Returns:
            결정례 상세 정보
        """
        params = {
            "target": "detc",
            "ID": decision_serial_number,
        }
        return await self._request("lawService.do", params)
    
    # ===========================================
    # 법령해석례 API (expc)
    # ===========================================
    
    async def get_interpretations_list(
        self,
        search: Optional[str] = None,
        field: Optional[str] = None,
        page: int = 1,
        display: int = 20,
    ) -> Dict[str, Any]:
        """
        법령해석례 목록 조회
        
        Args:
            search: 검색어
            field: 분야 필터
            page: 페이지 번호
            display: 페이지당 표시 개수
            
        Returns:
            법령해석례 목록 결과
        """
        params = {
            "target": "expc",
            "page": page,
            "display": display,
        }
        
        if search:
            params["query"] = search
        if field:
            params["분야"] = field
            
        return await self._request("lawSearch.do", params)
    
    async def get_interpretation_detail(self, interpretation_serial_number: int) -> Dict[str, Any]:
        """
        법령해석례 상세 조회
        
        Args:
            interpretation_serial_number: 법령해석례 고유 일련번호
            
        Returns:
            해석례 상세 정보
        """
        params = {
            "target": "expc",
            "ID": interpretation_serial_number,
        }
        return await self._request("lawService.do", params)
    
    # ===========================================
    # 법령 API (law)
    # ===========================================
    
    async def get_laws_list(
        self,
        search: Optional[str] = None,
        law_type: Optional[str] = None,
        page: int = 1,
        display: int = 20,
    ) -> Dict[str, Any]:
        """
        법령 목록 조회
        
        Args:
            search: 검색어 (법령명)
            law_type: 법령 구분 (법률, 대통령령 등)
            page: 페이지 번호
            display: 페이지당 표시 개수
            
        Returns:
            법령 목록 결과
        """
        params = {
            "target": "law",
            "page": page,
            "display": display,
        }
        
        if search:
            params["query"] = search
        if law_type:
            params["법령구분"] = law_type
            
        return await self._request("lawSearch.do", params)
    
    async def get_law_detail(self, law_serial_number: int) -> Dict[str, Any]:
        """
        법령 상세 조회
        
        Args:
            law_serial_number: 법령 고유 일련번호
            
        Returns:
            법령 상세 정보 (조문 포함)
        """
        params = {
            "target": "law",
            "MST": law_serial_number,
        }
        return await self._request("lawService.do", params)
    
    # ===========================================
    # 법령 용어 API (lstrm) - 소문자 필수!
    # ===========================================
    
    async def get_law_terms_list(
        self,
        search: Optional[str] = None,
        page: int = 1,
        display: int = 20,
    ) -> Dict[str, Any]:
        """
        법령 용어 목록 조회
        
        Args:
            search: 검색어 (용어명)
            page: 페이지 번호
            display: 페이지당 표시 개수
            
        Returns:
            법령 용어 목록 결과
        """
        params = {
            "target": "lstrm",  # 소문자 필수!
            "page": page,
            "display": display,
        }
        
        if search:
            params["query"] = search
            
        return await self._request("lawSearch.do", params)
    
    async def get_law_term_detail(self, term_serial_number: int) -> Dict[str, Any]:
        """
        법령 용어 상세 조회
        
        Args:
            term_serial_number: 용어 고유 일련번호
            
        Returns:
            용어 상세 정보
        """
        params = {
            "target": "lstrm",  # 소문자 필수!
            "trmSeqs": term_serial_number,
        }
        return await self._request("lawService.do", params)
    
    # ===========================================
    # HTML Fallback (JSON API 실패 시 HTML API 호출)
    # ===========================================
    
    async def get_case_detail_html(self, case_serial_number: int) -> Dict[str, Any]:
        """
        HTML API에서 판례 상세 정보 추출 (JSON API 실패 시 대체)
        파싱 결과가 비어있으면 외부 서비스로 JS 렌더링 시도
        """
        if not self._session:
            raise RuntimeError("클라이언트가 초기화되지 않았습니다. async with 문을 사용하세요.")
        
        # LSW 직접 요청 (리다이렉트 허용)
        detail_url = f"{self.LSW_URL}/precInfoP.do?precSeq={case_serial_number}&mode=0"
        
        try:
            async with self._session.get(detail_url, allow_redirects=True) as response:
                response.raise_for_status()
                final_url = str(response.url)
                html = await response.text()
            
            # 파싱 시도
            result = self._parse_detail_page(html, case_serial_number)
            
            # 결과 검증
            has_content = bool(
                result.get("사건번호") or 
                result.get("판결요지") or 
                result.get("판례내용")
            )
            
            if not has_content:
                # JS 렌더링 필요 - Selenium으로 시도
                print(f"[INFO] JS 렌더링 필요 (ID: {case_serial_number}), Selenium 시도...")
                return await self._fetch_with_selenium(detail_url, case_serial_number)
            
            return result
                    
        except aiohttp.ClientError as e:
            print(f"HTML 요청 실패: {e}")
            raise
    
    def _selenium_fetch_sync(self, url: str, case_serial_number: int) -> Dict[str, Any]:
        """
        Selenium 동기 크롤링 (ThreadPoolExecutor에서 실행됨)
        
        이 메서드는 동기 함수이며, _fetch_with_selenium()에서
        run_in_executor를 통해 비동기로 호출됩니다.
        """
        result = {
            "판례정보일련번호": str(case_serial_number),
            "사건명": "",
            "사건번호": "",
            "선고일자": "",
            "법원명": "",
            "판결유형": "",
            "판시사항": "",
            "판결요지": "",
            "참조조문": "",
            "참조판례": "",
            "판례내용": "",
        }
        
        driver = None
        try:
            # Chrome 옵션 설정
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # WebDriver 초기화
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            
            # 페이지 로드
            driver.get(url)
            
            # JS 렌더링 대기
            time.sleep(3)
            
            # 동적 콘텐츠 대기 시도
            try:
                WebDriverWait(driver, 7).until(
                    lambda d: d.find_element(By.TAG_NAME, "body").text.strip() != ""
                )
            except TimeoutException:
                pass
            
            # 렌더링된 HTML 가져오기
            html = driver.page_source
            final_url = driver.current_url
            
            print(f"[DEBUG] Selenium final URL: {final_url}")
            
            # 파싱 시도
            parsed = self._parse_external_page(html, case_serial_number)
            
            # 결과 병합
            for key, value in parsed.items():
                if value:
                    result[key] = value
            
            # 콘텐츠 검증
            has_content = bool(
                result.get("사건번호") or 
                result.get("판결요지") or 
                result.get("판례내용")
            )
            
            if not has_content:
                result["_parse_failed"] = True
                result["_error"] = "Selenium 렌더링 후에도 콘텐츠 파싱 실패"
            
            return result
            
        except WebDriverException as e:
            result["_error"] = f"WebDriver 오류: {str(e)}"
            result["_parse_failed"] = True
            return result
        except Exception as e:
            result["_error"] = f"Selenium 오류: {str(e)}"
            result["_parse_failed"] = True
            return result
        finally:
            if driver:
                driver.quit()
    
    async def _fetch_with_selenium(self, url: str, case_serial_number: int) -> Dict[str, Any]:
        """
        Selenium headless Chrome으로 JS 렌더링 후 파싱 (비동기 래퍼)
        
        동기 Selenium 코드를 ThreadPoolExecutor에서 실행하여
        여러 크롤링 작업을 병렬로 처리할 수 있습니다.
        """
        loop = asyncio.get_event_loop()
        executor = get_selenium_executor()
        
        # 동기 함수를 ThreadPool에서 실행
        return await loop.run_in_executor(
            executor,
            self._selenium_fetch_sync,
            url,
            case_serial_number
        )
    
    def _parse_external_page(self, html: str, case_serial_number: int) -> Dict[str, Any]:
        """
        외부 시스템 페이지 파싱 (국세법령정보시스템 등)
        
        국세법령정보시스템 HTML 구조:
        - 사건명: div.title > strong.bold
        - 판결유형: div.title > em.com_badge (예: "국승", "국패")
        - 사건번호: div.bo_head ul > li:first > strong
        - 생산일자: "생산일자" li > span.num
        - 참조조문: div.rel_group > div > a
        - 요지: div[data-center-type="body_content_gist"] > p
        - 판결내용: div[data-center-type="body_content_cntn"] > p
        - 상세내용: div#cntnWrap_html
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            "판례정보일련번호": str(case_serial_number),
            "사건명": "",
            "사건번호": "",
            "선고일자": "",
            "법원명": "",
            "판결유형": "",
            "판시사항": "",
            "판결요지": "",
            "참조조문": "",
            "참조판례": "",
            "판례내용": "",
        }
        
        # ========================================
        # 국세법령정보시스템 구조 파싱
        # ========================================
        
        # 사건명: div.title > strong.bold
        title_div = soup.find('div', class_='title')
        if title_div:
            title_strong = title_div.find('strong', class_='bold')
            if title_strong:
                result["사건명"] = title_strong.get_text(strip=True)
        
        # 판결유형: div.title > em.com_badge (국승, 국패 등)
        if title_div:
            badge = title_div.find('em', class_='com_badge')
            if badge:
                badge_text = badge.get_text(strip=True)
                # 국승 -> 처분청 승소, 국패 -> 처분청 패소
                if badge_text == "국승":
                    result["판결유형"] = "처분청 승소"
                elif badge_text == "국패":
                    result["판결유형"] = "처분청 패소"
                else:
                    result["판결유형"] = badge_text
        
        # 사건번호, 선고일자: bo_head 영역의 ul > li들
        bo_head = soup.find('div', class_='bo_head')
        if bo_head:
            li_items = bo_head.find_all('li')
            for li in li_items:
                strong = li.find('strong')
                if strong:
                    label = strong.get_text(strip=True)
                    
                    # 첫번째 li의 strong이 사건번호 (대법원-2025-두-34568)
                    if '-' in label and any(c.isdigit() for c in label):
                        result["사건번호"] = label
                    
                    # 생산일자 = 선고일자
                    if "생산일자" in label:
                        span = li.find('span', class_='num')
                        if span:
                            date_text = span.get_text(strip=True).replace('.', '')
                            if len(date_text) >= 8:
                                result["선고일자"] = date_text[:8]
        
        # 참조조문: div.rel_group > div > a 링크들
        rel_group = soup.find('div', class_='rel_group')
        if rel_group:
            links = rel_group.find_all('a', class_='txt_link')
            refs = [a.get_text(strip=True) for a in links]
            if refs:
                result["참조조문"] = ', '.join(refs)
        
        # 요지 (판결요지): div[data-center-type="body_content_gist"]
        gist_div = soup.find('div', {'data-center-type': 'body_content_gist'})
        if gist_div:
            p_tag = gist_div.find('p')
            if p_tag:
                result["판결요지"] = p_tag.get_text(strip=True)
        
        # 판결내용 (간략): div[data-center-type="body_content_cntn"]
        cntn_div = soup.find('div', {'data-center-type': 'body_content_cntn'})
        if cntn_div:
            p_tag = cntn_div.find('p')
            if p_tag:
                content = p_tag.get_text(separator='\n', strip=True)
                if content:
                    result["판례내용"] = content
        
        # 상세내용 (전문): div#cntnWrap_html - 더 자세한 내용
        html_cntn = soup.find('div', id='cntnWrap_html')
        if html_cntn:
            full_content = html_cntn.get_text(separator='\n', strip=True)
            if full_content and len(full_content) > len(result.get("판례내용", "")):
                result["판례내용"] = full_content[:15000]  # 최대 15000자
        
        # 법원명 추출: 사건번호에서 또는 텍스트에서
        if result["사건번호"]:
            if "대법원" in result["사건번호"]:
                result["법원명"] = "대법원"
            elif "고등법원" in result["사건번호"]:
                result["법원명"] = "고등법원"
        
        if not result["법원명"]:
            full_text = soup.get_text()
            court_match = re.search(r'(대법원|서울고등법원|고등법원|지방법원|행정법원)', full_text)
            if court_match:
                result["법원명"] = court_match.group(1)
        
        # ========================================
        # Fallback: 텍스트 기반 파싱 (위에서 못 찾은 경우)
        # ========================================
        full_text = soup.get_text(separator='\n', strip=True)
        
        # 사건명 fallback
        if not result["사건명"]:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                if title_text and len(title_text) < 200:
                    result["사건명"] = title_text
        
        # 사건번호 fallback
        if not result["사건번호"]:
            case_match = re.search(r'(\d{4}[가-힣]+\d+)', full_text)
            if case_match:
                result["사건번호"] = case_match.group(1)
        
        # 선고일자 fallback
        if not result["선고일자"]:
            date_patterns = [
                r'선고일자[:\s-]*(\d{4})\.?(\d{1,2})\.?(\d{1,2})',
                r'(\d{4})\.(\d{1,2})\.(\d{1,2})\.?\s*선고',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, full_text)
                if match:
                    result["선고일자"] = f"{match.group(1)}{match.group(2).zfill(2)}{match.group(3).zfill(2)}"
                    break
        
        # 판결유형 fallback
        if not result["판결유형"]:
            verdict_patterns = [
                r'(처분청\s*승소|처분청\s*패소)',
                r'(원고\s*승소|원고\s*패소|피고\s*승소|피고\s*패소)',
                r'(상고\s*기각|상고\s*인용|파기\s*환송)',
            ]
            for pattern in verdict_patterns:
                match = re.search(pattern, full_text)
                if match:
                    result["판결유형"] = match.group(1).replace(' ', '')
                    break
        
        # 판례내용 fallback
        if not result["판례내용"]:
            content_match = re.search(r'(주\s*문.+)', full_text, re.DOTALL)
            if content_match:
                result["판례내용"] = content_match.group(1).strip()[:15000]
        
        return result
    
    def _parse_detail_page(self, html: str, case_serial_number: int) -> Dict[str, Any]:
        """판례 상세 페이지 파싱 (범용)"""
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            "판례정보일련번호": str(case_serial_number),
            "사건명": "",
            "사건번호": "",
            "선고일자": "",
            "법원명": "",
            "판시사항": "",
            "판결요지": "",
            "참조조문": "",
            "참조판례": "",
            "판례내용": "",
        }
        
        # === 법제처 페이지 파싱 ===
        
        # 사건명
        precNm = soup.find('input', {'id': 'precNm'})
        if precNm and precNm.get('value'):
            result["사건명"] = precNm['value']
        else:
            h2 = soup.find('h2', {'data-brl-use': 'PH/H1'})
            if h2:
                result["사건명"] = h2.get_text(strip=True)
        
        # 사건번호
        precNo = soup.find('input', {'id': 'precNo'})
        if precNo and precNo.get('value'):
            result["사건번호"] = precNo['value']
        
        # 선고일자
        precYd = soup.find('input', {'id': 'precYd'})
        if precYd and precYd.get('value'):
            result["선고일자"] = precYd['value']
        
        # 법원명
        match = re.search(r'\[(\S+법원|\S+재판소)\s+\d{4}\.', html)
        if match:
            result["법원명"] = match.group(1)
        
        # 본문 컨테이너 찾기
        trial_section = soup.find('div', {'class': 'trial-section', 'data-prec-seq': str(case_serial_number)})
        con_scroll = soup.find('div', {'id': 'conScroll'})
        container = trial_section or con_scroll or soup
        
        # 판시사항
        sa = container.find('h4', {'id': f'sa-{case_serial_number}'})
        if sa:
            p = sa.find_next_sibling('p', class_='pty4')
            if p:
                result["판시사항"] = p.get_text(separator='\n', strip=True)
        
        # 판결요지
        yo = container.find('h4', {'id': f'yo-{case_serial_number}'})
        if yo:
            p = yo.find_next_sibling('p', class_='pty4')
            if p:
                result["판결요지"] = p.get_text(separator='\n', strip=True)
        
        # 참조조문
        jo = container.find('h4', {'id': f'conLsJo-{case_serial_number}'})
        if jo:
            p = jo.find_next_sibling('p', class_='pty4')
            if p:
                result["참조조문"] = p.get_text(separator='\n', strip=True)
        
        # 참조판례
        prec = container.find('h4', {'id': f'conPrec-{case_serial_number}'})
        if prec:
            p = prec.find_next_sibling('p', class_='pty4')
            if p:
                result["참조판례"] = p.get_text(separator='\n', strip=True)
        
        # 전문
        jun = container.find('h4', {'id': f'jun-{case_serial_number}'})
        if jun:
            parts = []
            for sib in jun.find_next_siblings():
                if sib.name == 'h4':
                    break
                if sib.get('class') and 'trial-section' in sib.get('class', []):
                    break
                parts.append(sib.get_text(separator='\n', strip=True))
            result["판례내용"] = '\n'.join(filter(None, parts))
        
        return result
    
    async def get_case_detail_with_fallback(self, case_serial_number: int) -> Dict[str, Any]:
        """
        판례 상세 조회 (XML 시도 후 실패하면 HTML로 대체)
        
        Args:
            case_serial_number: 판례 고유 일련번호
            
        Returns:
            판례 상세 정보
        """
        # 먼저 XML API 시도
        try:
            result = await self.get_case_detail(case_serial_number)
            
            # 오류 응답 확인 (다양한 오류 패턴)
            error_messages = ["일치하는 판례가 없습니다", "데이터가 없습니다", "조회된 데이터가 없습니다"]
            result_str = str(result)
            
            for error_msg in error_messages:
                if error_msg in result_str:
                    print(f"XML API 오류 응답 (ID: {case_serial_number}), HTML 크롤링으로 대체")
                    return await self.get_case_detail_html(case_serial_number)
            
            # 핵심 콘텐츠 확인 (사건명 + 본문 중 하나라도 있어야 정상)
            has_content = bool(
                result.get("판례내용") or 
                result.get("판결요지") or 
                result.get("판시사항")
            )
            
            if not has_content:
                print(f"XML API 본문 없음 (ID: {case_serial_number}), HTML 크롤링으로 대체")
                return await self.get_case_detail_html(case_serial_number)
            
            return result
            
        except Exception as e:
            print(f"XML API 오류 (ID: {case_serial_number}): {e}, HTML 크롤링으로 대체")
            return await self.get_case_detail_html(case_serial_number)
    
    # ===========================================
    # 사건번호 파싱 유틸리티
    # ===========================================
    
    @staticmethod
    def parse_case_title(title: str) -> Dict[str, str]:
        """
        판례 제목에서 법원명과 사건번호 추출
        
        예시: 
            "서울고등법원-2022-누-38108" → {"court_name": "서울고등법원", "case_number": "2022누38108"}
            "서울고등법원(인천)-2025-누-10220" → {"court_name": "서울고등법원(인천)", "case_number": "2025누10220"}
            "대법원-2025-두-34679" → {"court_name": "대법원", "case_number": "2025두34679"}
            "평택지원-2025-가단-53100" → {"court_name": "평택지원", "case_number": "2025가단53100"}
            "광주고등법원(전주)-2024-누-1066" → {"court_name": "광주고등법원(전주)", "case_number": "2024누1066"}
            "서울고등법원2025누6453" → {"court_name": "서울고등법원", "case_number": "2025누6453"}
            "대전고등법원2025누385" → {"court_name": "대전고등법원", "case_number": "2025누385"}
            "2023다12345" → {"court_name": "", "case_number": "2023다12345"}
            
        Args:
            title: 판례 제목 또는 사건번호 문자열
            
        Returns:
            {"court_name": str, "case_number": str}
        """
        if not title:
            return {"court_name": "", "case_number": ""}
        
        # 법원/지원 패턴 (대법원, OO법원, OO지원, 괄호 포함)
        court_pattern = r'(?:법원|대법원|지원)(?:\([^)]+\))?'
        
        # 패턴 1: "법원명-년도-종류-번호" 형식 (하이픈으로 구분)
        # 예: "서울고등법원(인천)-2025-누-10220", "평택지원-2025-가단-53100"
        pattern1 = rf'^(.+?{court_pattern})-(\d{{4}})-([가-힣]+)-(\d+)$'
        match = re.match(pattern1, title)
        if match:
            court_name = match.group(1)
            year = match.group(2)
            case_type = match.group(3)
            number = match.group(4)
            case_number = f"{year}{case_type}{number}"
            return {"court_name": court_name, "case_number": case_number}
        
        # 패턴 2: "법원명년도종류번호" 형식 (하이픈 없이 붙어있음)
        # 예: "서울고등법원2025누6453", "대전고등법원2025누385"
        pattern2 = rf'^(.+?{court_pattern})(\d{{4}})([가-힣]+)(\d+)$'
        match = re.match(pattern2, title)
        if match:
            court_name = match.group(1)
            year = match.group(2)
            case_type = match.group(3)
            number = match.group(4)
            case_number = f"{year}{case_type}{number}"
            return {"court_name": court_name, "case_number": case_number}
        
        # 패턴 3: "법원명 년도종류번호" 형식 (공백으로 구분)
        pattern3 = rf'^(.+?{court_pattern})\s+(\d{{4}}[가-힣]+\d+)$'
        match = re.match(pattern3, title)
        if match:
            return {"court_name": match.group(1), "case_number": match.group(2)}
        
        # 패턴 4: 순수 사건번호만 "년도종류번호" 형식 (예: 2023다12345, 93누1077)
        pattern4 = r'^(\d{2,4})([가-힣]+)(\d+)$'
        match = re.match(pattern4, title)
        if match:
            return {"court_name": "", "case_number": title}
        
        # 매칭 실패시 원본 반환
        return {"court_name": "", "case_number": title}
    
    @staticmethod
    def extract_court_from_case_number(case_number: str, default_court: str = "") -> str:
        """
        사건번호에서 법원 유형 추정
        
        Args:
            case_number: 사건번호 (예: 2023다12345, 93누1077)
            default_court: 기본 법원명
            
        Returns:
            추정된 법원명
        """
        if not case_number:
            return default_court
        
        # 사건 종류별 법원 매핑
        case_type_mapping = {
            "다": "대법원",  # 민사
            "도": "대법원",  # 형사
            "두": "대법원",  # 행정
            "나": "고등법원",  # 민사 항소
            "노": "고등법원",  # 형사 항소
            "누": "고등법원",  # 행정 항소
            "가단": "지방법원",  # 민사 단독
            "고단": "지방법원",  # 형사 단독
            "구합": "지방법원",  # 행정 합의
            "허": "특허법원",  # 특허
            "헌가": "헌법재판소",  # 위헌법률심판
            "헌바": "헌법재판소",  # 헌법소원
            "헌마": "헌법재판소",  # 헌법소원
        }
        
        # 사건번호에서 종류 추출 (2~4자리 연도 지원)
        match = re.search(r'\d{2,4}([가-힣]+)', case_number)
        if match:
            case_type = match.group(1)
            for key, court in case_type_mapping.items():
                if case_type.startswith(key):
                    return court
        
        return default_court


# 편의 함수
async def test_api_connection() -> bool:
    """
    API 연결 테스트
    
    Returns:
        연결 성공 여부
    """
    try:
        async with LawAPIClient() as client:
            result = await client.get_cases_list(page=1, display=1)
            return "totalCnt" in result
    except Exception as e:
        print(f"API 연결 테스트 실패: {e}")
        return False


async def test_html_fallback(case_id: int = 347410) -> Dict[str, Any]:
    """
    HTML Fallback 기능 테스트
    
    Args:
        case_id: 테스트할 판례 ID
        
    Returns:
        파싱된 판례 데이터
    """
    async with LawAPIClient() as client:
        return await client.get_case_detail_with_fallback(case_id)


async def test_law_api() -> bool:
    """
    법령 API 연결 테스트
    
    Returns:
        연결 성공 여부
    """
    try:
        async with LawAPIClient() as client:
            result = await client.get_laws_list(search="민법", page=1, display=1)
            return "totalCnt" in result or len(result.get("items", [])) > 0
    except Exception as e:
        print(f"법령 API 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    # 테스트 실행
    async def main():
        print("=" * 50)
        print("법제처 API 연결 테스트")
        print("=" * 50)
        
        # 1. 기본 연결 테스트
        print("\n1. 기본 API 연결 테스트...")
        success = await test_api_connection()
        if success:
            print("✅ API 연결 성공")
        else:
            print("❌ API 연결 실패")
        
        # 2. 법령 API 테스트
        print("\n2. 법령 API 테스트...")
        law_success = await test_law_api()
        if law_success:
            print("✅ 법령 API 성공")
        else:
            print("❌ 법령 API 실패")
        
        # 3. HTML Fallback 테스트
        print("\n3. HTML Fallback 테스트...")
        try:
            result = await test_html_fallback()
            if result.get("사건명") or result.get("판례내용"):
                print("✅ HTML Fallback 성공")
                print(f"   - 사건명: {result.get('사건명', 'N/A')[:50]}...")
            else:
                print("⚠️  HTML Fallback: 데이터 부분 추출")
        except Exception as e:
            print(f"❌ HTML Fallback 실패: {e}")
        
        # 4. 사건번호 파싱 테스트
        print("\n4. 사건번호 파싱 테스트...")
        test_cases = [
            "서울고등법원-2022-누-38108",
            "2023다12345",
            "대법원 2023다12345",
        ]
        for test in test_cases:
            parsed = LawAPIClient.parse_case_title(test)
            print(f"   '{test}' → court: '{parsed['court_name']}', case: '{parsed['case_number']}'")
        
        print("\n" + "=" * 50)
        print("테스트 완료")
    
    asyncio.run(main())
