"""
법제처 OpenAPI 클라이언트
판례, 헌재결정례, 법령해석례 API 호출
"""
import asyncio
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List, Any
from datetime import datetime
import aiohttp

from app.config import settings


class LawAPIClient:
    """
    법제처 OpenAPI 비동기 클라이언트
    
    사용 예시:
        async with LawAPIClient() as client:
            cases = await client.get_cases_list(search="손해배상", page=1)
            case_detail = await client.get_case_detail(판례일련번호=12345)
    """
    
    BASE_URL = "https://www.law.go.kr/DRF"
    
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
        
        # 목록 아이템 파싱 (prec, detc, expc 등)
        for item in root.findall(".//prec") + root.findall(".//detc") + root.findall(".//expc"):
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
        
        # 기본 파라미터 추가
        params = {
            "OC": self.oc,
            "type": "XML",
            **params
        }
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with self._session.get(url, params=params) as response:
                response.raise_for_status()
                text = await response.text()
                return self._parse_xml(text)
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
    
    async def get_case_detail(self, 판례일련번호: int) -> Dict[str, Any]:
        """
        판례 상세 조회
        
        Args:
            판례일련번호: 판례 고유 일련번호
            
        Returns:
            판례 상세 정보
        """
        params = {
            "target": "prec",
            "ID": 판례일련번호,
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
    
    async def get_constitutional_detail(self, 결정례일련번호: int) -> Dict[str, Any]:
        """
        헌재결정례 상세 조회
        
        Args:
            결정례일련번호: 결정례 고유 일련번호
            
        Returns:
            헌재결정례 상세 정보
        """
        params = {
            "target": "detc",
            "ID": 결정례일련번호,
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
    
    async def get_interpretation_detail(self, 법령해석례일련번호: int) -> Dict[str, Any]:
        """
        법령해석례 상세 조회
        
        Args:
            법령해석례일련번호: 법령해석례 고유 일련번호
            
        Returns:
            법령해석례 상세 정보
        """
        params = {
            "target": "expc",
            "ID": 법령해석례일련번호,
        }
        return await self._request("lawService.do", params)


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


if __name__ == "__main__":
    # 테스트 실행
    async def main():
        print("법제처 API 연결 테스트...")
        success = await test_api_connection()
        if success:
            print("✅ API 연결 성공")
        else:
            print("❌ API 연결 실패")
    
    asyncio.run(main())
