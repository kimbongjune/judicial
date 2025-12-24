"""
법령 용어 API 라우터
"""
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/law-terms", tags=["법령용어"])


class LawTermResponse(BaseModel):
    """법령 용어 응답 모델"""
    term: str
    definition: Optional[str] = None
    source: Optional[str] = None
    law_name: Optional[str] = None
    article_number: Optional[str] = None


class LawTermSearchResponse(BaseModel):
    """법령 용어 검색 응답"""
    total: int
    items: List[LawTermResponse]


# 캐시된 법령 용어 데이터 (실제로는 DB에서 조회)
CACHED_LAW_TERMS = {
    "채권": {
        "term": "채권",
        "definition": "특정인(채권자)이 다른 특정인(채무자)에 대하여 일정한 행위(급부)를 청구할 수 있는 권리",
        "source": "민법",
        "law_name": "민법",
        "article_number": "제373조"
    },
    "채무": {
        "term": "채무",
        "definition": "특정인(채무자)이 다른 특정인(채권자)에게 일정한 행위(급부)를 하여야 할 의무",
        "source": "민법",
        "law_name": "민법",
        "article_number": "제373조"
    },
    "불법행위": {
        "term": "불법행위",
        "definition": "고의 또는 과실로 인한 위법행위로 타인에게 손해를 가하는 행위",
        "source": "민법",
        "law_name": "민법",
        "article_number": "제750조"
    },
    "손해배상": {
        "term": "손해배상",
        "definition": "타인에게 가한 손해를 금전 또는 원상회복으로 보상하는 것",
        "source": "민법",
        "law_name": "민법",
        "article_number": "제750조, 제751조"
    },
    "위헌": {
        "term": "위헌",
        "definition": "법률이나 명령 등이 헌법에 위반되는 것",
        "source": "헌법재판소법",
        "law_name": "헌법재판소법",
        "article_number": "제41조"
    },
    "고의": {
        "term": "고의",
        "definition": "자기의 행위가 일정한 결과를 발생시킬 것을 인식하면서 그 행위를 하는 심리상태",
        "source": "형법",
        "law_name": "형법",
        "article_number": "제13조"
    },
    "과실": {
        "term": "과실",
        "definition": "주의의무를 위반하여 일정한 사실을 인식하지 못한 심리상태",
        "source": "형법",
        "law_name": "형법",
        "article_number": "제14조"
    },
    "항소": {
        "term": "항소",
        "definition": "제1심 법원의 판결에 불복하여 상급법원에 재판을 구하는 불복신청",
        "source": "민사소송법",
        "law_name": "민사소송법",
        "article_number": "제390조"
    },
    "상고": {
        "term": "상고",
        "definition": "항소심 법원의 판결에 불복하여 대법원에 재판을 구하는 불복신청",
        "source": "민사소송법",
        "law_name": "민사소송법",
        "article_number": "제422조"
    },
    "기각": {
        "term": "기각",
        "definition": "소송에서 청구 또는 신청이 이유 없다고 하여 배척하는 재판",
        "source": "민사소송법",
        "law_name": "민사소송법",
        "article_number": "제208조"
    },
    "각하": {
        "term": "각하",
        "definition": "소송요건의 흠결을 이유로 본안에 대한 판단 없이 소를 배척하는 재판",
        "source": "민사소송법",
        "law_name": "민사소송법",
        "article_number": "제219조"
    },
    "파기환송": {
        "term": "파기환송",
        "definition": "상급법원이 하급법원의 판결을 파기하고 사건을 원심법원에 다시 보내는 것",
        "source": "민사소송법",
        "law_name": "민사소송법",
        "article_number": "제436조"
    },
}


@router.get("", response_model=LawTermSearchResponse)
async def search_law_terms(
    term: Optional[str] = Query(None, description="검색할 용어"),
    q: Optional[str] = Query(None, description="검색어"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """
    법령 용어 검색
    
    - **term**: 정확한 용어명으로 검색
    - **q**: 용어명 또는 정의에서 검색
    """
    search_term = term or q
    
    if search_term:
        # 정확한 매칭
        if search_term in CACHED_LAW_TERMS:
            return LawTermSearchResponse(
                total=1,
                items=[LawTermResponse(**CACHED_LAW_TERMS[search_term])]
            )
        
        # 부분 매칭
        matched = []
        for key, value in CACHED_LAW_TERMS.items():
            if search_term in key or search_term in (value.get("definition") or ""):
                matched.append(LawTermResponse(**value))
        
        return LawTermSearchResponse(
            total=len(matched),
            items=matched[(page-1)*size:page*size]
        )
    
    # 전체 목록
    all_terms = [LawTermResponse(**v) for v in CACHED_LAW_TERMS.values()]
    return LawTermSearchResponse(
        total=len(all_terms),
        items=all_terms[(page-1)*size:page*size]
    )


@router.get("/{term_name}", response_model=LawTermResponse)
async def get_law_term(term_name: str):
    """
    특정 법령 용어 조회
    """
    if term_name in CACHED_LAW_TERMS:
        return LawTermResponse(**CACHED_LAW_TERMS[term_name])
    
    raise HTTPException(status_code=404, detail="해당 용어를 찾을 수 없습니다")
