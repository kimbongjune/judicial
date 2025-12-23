# 내부 API 정의서

## 1. 개요

본 문서는 법률 판례 검색 시스템의 내부 REST API 명세입니다.

### 1.1 기본 정보

| 항목 | 내용 |
|------|------|
| Base URL | `http://localhost:8000/api/v1` |
| 프로토콜 | HTTP/HTTPS |
| 응답 형식 | JSON |
| 인코딩 | UTF-8 |
| API 문서 | `/docs` (Swagger UI), `/redoc` (ReDoc) |

### 1.2 공통 응답 구조

```json
{
  "success": true,
  "data": { ... },
  "message": "성공",
  "meta": {
    "total": 100,
    "page": 1,
    "size": 20,
    "total_pages": 5
  }
}
```

### 1.3 에러 응답 구조

```json
{
  "success": false,
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "판례를 찾을 수 없습니다.",
    "detail": "ID: 123456에 해당하는 판례가 존재하지 않습니다."
  }
}
```

### 1.4 HTTP 상태 코드

| 코드 | 설명 |
|------|------|
| 200 | 성공 |
| 201 | 생성됨 |
| 400 | 잘못된 요청 |
| 404 | 리소스 없음 |
| 422 | 유효성 검증 실패 |
| 500 | 서버 오류 |

---

## 2. 판례 검색 API

### 2.1 키워드 검색

**판례를 키워드로 검색합니다.**

```
GET /api/v1/cases/search
```

#### 요청 파라미터 (Query String)

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| q | string | ✅ | - | 검색어 |
| court | string | - | - | 법원 필터 (comma separated) |
| case_type | string | - | - | 사건유형 필터 |
| from_date | string | - | - | 시작일 (YYYY-MM-DD) |
| to_date | string | - | - | 종료일 (YYYY-MM-DD) |
| page | integer | - | 1 | 페이지 번호 |
| size | integer | - | 20 | 페이지 크기 (max: 100) |
| sort | string | - | relevance | 정렬 기준 (relevance, date_desc, date_asc) |

#### 요청 예시

```bash
GET /api/v1/cases/search?q=손해배상&court=대법원&from_date=2023-01-01&page=1&size=20
```

#### 응답 예시

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 12345,
        "serial_number": "123456",
        "case_name": "손해배상(기)",
        "case_number": "2023다12345",
        "decision_date": "2023-12-15",
        "court_name": "대법원",
        "case_type": "민사",
        "judgment_type": "판결",
        "holding_summary": "불법행위로 인한 손해배상청구에서...",
        "relevance_score": 0.95
      }
    ]
  },
  "meta": {
    "total": 156,
    "page": 1,
    "size": 20,
    "total_pages": 8
  }
}
```

---

### 2.2 자연어 검색 (유사도 기반)

**자연어 질의로 의미적으로 유사한 판례를 검색합니다.**

```
POST /api/v1/cases/search/semantic
```

#### 요청 본문

```json
{
  "query": "이웃집에서 나는 소음으로 인해 정신적 피해를 입었을 때 손해배상을 받을 수 있는지",
  "top_k": 20,
  "threshold": 0.5,
  "filters": {
    "court": ["대법원", "고등법원"],
    "case_type": "민사",
    "from_date": "2020-01-01"
  }
}
```

#### 요청 필드 설명

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| query | string | ✅ | - | 자연어 검색 질의 |
| top_k | integer | - | 10 | 반환할 결과 수 |
| threshold | float | - | 0.3 | 최소 유사도 점수 (0~1) |
| filters | object | - | - | 추가 필터 조건 |

#### 응답 예시

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 12345,
        "case_name": "손해배상(기)",
        "case_number": "2023다12345",
        "decision_date": "2023-12-15",
        "court_name": "대법원",
        "case_type": "민사",
        "holding_summary": "층간 소음으로 인한 정신적 손해...",
        "similarity_score": 0.89,
        "matched_content": "층간소음으로 인한 정신적 고통에 대하여..."
      }
    ],
    "query_embedding_time_ms": 45,
    "search_time_ms": 12
  },
  "meta": {
    "total": 15,
    "model": "jhgan/ko-sroberta-multitask"
  }
}
```

---

### 2.3 유사 판례 검색

**특정 판례와 유사한 판례를 검색합니다.**

```
GET /api/v1/cases/{case_id}/similar
```

#### 경로 파라미터

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| case_id | integer | 판례 ID |

#### 요청 파라미터 (Query String)

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| top_k | integer | - | 10 | 반환할 유사 판례 수 |
| threshold | float | - | 0.5 | 최소 유사도 점수 |

#### 응답 예시

```json
{
  "success": true,
  "data": {
    "source_case": {
      "id": 12345,
      "case_number": "2023다12345",
      "case_name": "손해배상(기)"
    },
    "similar_cases": [
      {
        "id": 12346,
        "case_number": "2022다98765",
        "case_name": "손해배상(기)",
        "decision_date": "2022-10-20",
        "court_name": "대법원",
        "similarity_score": 0.92,
        "common_keywords": ["불법행위", "손해배상", "위자료"]
      }
    ]
  }
}
```

---

### 2.4 텍스트 기반 유사 판례 검색

**입력된 텍스트와 유사한 판례를 검색합니다.**

```
POST /api/v1/cases/similar/by-text
```

#### 요청 본문

```json
{
  "text": "피고는 원고 소유의 건물 옆에서 대규모 건설공사를 진행하면서 적절한 방호조치 없이 공사를 진행하여 원고 건물에 균열이 발생하였고...",
  "top_k": 10,
  "threshold": 0.5
}
```

#### 응답 예시

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 12350,
        "case_number": "2021다54321",
        "case_name": "손해배상(기)",
        "similarity_score": 0.87,
        "highlight": "건설공사로 인한 인접 건물 손해..."
      }
    ]
  }
}
```

---

## 3. 판례 조회 API

### 3.1 판례 상세 조회

**판례의 상세 정보를 조회합니다.**

```
GET /api/v1/cases/{case_id}
```

#### 경로 파라미터

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| case_id | integer | 판례 ID |

#### 응답 예시

```json
{
  "success": true,
  "data": {
    "id": 12345,
    "serial_number": "123456",
    "case_name": "손해배상(기)",
    "case_number": "2023다12345",
    "decision_date": "2023-12-15",
    "decision_type": "선고",
    "court_name": "대법원",
    "case_type": "민사",
    "judgment_type": "판결",
    "holding": "[1] 불법행위로 인한 손해배상청구에서...\n[2] 위자료 산정의 기준...",
    "summary": "[1] 불법행위로 인한 손해배상책임이 성립하려면...",
    "full_text": "【원고, 피상고인】 원고...",
    "reference_articles": [
      {
        "law_name": "민법",
        "article": "제750조",
        "content": "불법행위의 내용"
      }
    ],
    "reference_cases": [
      {
        "case_number": "2019다12345",
        "court_name": "대법원",
        "decision_date": "2020-01-01"
      }
    ],
    "source_url": "https://www.law.go.kr/...",
    "created_at": "2023-12-20T10:30:00Z",
    "updated_at": "2023-12-20T10:30:00Z"
  }
}
```

---

### 3.2 사건번호로 판례 조회

**사건번호로 판례를 조회합니다.**

```
GET /api/v1/cases/by-number/{case_number}
```

#### 경로 파라미터

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| case_number | string | 사건번호 (URL 인코딩 필요) |

#### 요청 예시

```bash
GET /api/v1/cases/by-number/2023%EB%8B%A412345
```

---

### 3.3 판례 목록 조회

**판례 목록을 조회합니다 (필터링/정렬 지원).**

```
GET /api/v1/cases
```

#### 요청 파라미터 (Query String)

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| court | string | - | - | 법원 필터 |
| case_type | string | - | - | 사건유형 |
| from_date | string | - | - | 시작일 |
| to_date | string | - | - | 종료일 |
| page | integer | - | 1 | 페이지 번호 |
| size | integer | - | 20 | 페이지 크기 |
| sort | string | - | date_desc | 정렬 기준 |

---

## 4. 헌재결정례 API

### 4.1 헌재결정례 검색

```
GET /api/v1/constitutional/search
```

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| q | string | ✅ | 검색어 |
| decision_type | string | - | 결정유형 (위헌, 합헌 등) |
| case_type | string | - | 사건유형 |
| page | integer | - | 페이지 번호 |
| size | integer | - | 페이지 크기 |

### 4.2 헌재결정례 상세 조회

```
GET /api/v1/constitutional/{id}
```

### 4.3 헌재결정례 유사 검색

```
POST /api/v1/constitutional/search/semantic
```

---

## 5. 법령해석례 API

### 5.1 법령해석례 검색

```
GET /api/v1/interpretations/search
```

### 5.2 법령해석례 상세 조회

```
GET /api/v1/interpretations/{id}
```

---

## 6. 법령 API

### 6.1 법령 검색

```
GET /api/v1/laws/search
```

### 6.2 법령 상세 조회

```
GET /api/v1/laws/{mst_seq}
```

### 6.3 법령 조문 조회

```
GET /api/v1/laws/{mst_seq}/articles/{article_number}
```

---

## 7. 필터 옵션 API

### 7.1 법원 목록 조회

**검색 필터에 사용할 법원 목록을 조회합니다.**

```
GET /api/v1/filters/courts
```

#### 응답 예시

```json
{
  "success": true,
  "data": [
    {"code": "400201", "name": "대법원", "count": 50000},
    {"code": "400202", "name": "고등법원", "count": 80000},
    {"code": "400204", "name": "지방법원", "count": 120000}
  ]
}
```

### 7.2 사건유형 목록 조회

```
GET /api/v1/filters/case-types
```

#### 응답 예시

```json
{
  "success": true,
  "data": [
    {"code": "400101", "name": "민사", "count": 150000},
    {"code": "400102", "name": "형사", "count": 80000},
    {"code": "400103", "name": "행정", "count": 20000}
  ]
}
```

### 7.3 연도별 통계 조회

```
GET /api/v1/filters/years
```

---

## 8. 통계 API

### 8.1 전체 통계

```
GET /api/v1/stats/overview
```

#### 응답 예시

```json
{
  "success": true,
  "data": {
    "total_cases": 250000,
    "total_constitutional": 10000,
    "total_interpretations": 50000,
    "last_sync": "2023-12-20T02:00:00Z",
    "index_status": "ready",
    "model_version": "jhgan/ko-sroberta-multitask"
  }
}
```

### 8.2 검색 통계

```
GET /api/v1/stats/search
```

#### 응답 예시

```json
{
  "success": true,
  "data": {
    "today_searches": 1500,
    "popular_keywords": [
      {"keyword": "손해배상", "count": 150},
      {"keyword": "부당해고", "count": 120}
    ],
    "avg_response_time_ms": 250
  }
}
```

---

## 9. 헬스체크 API

### 9.1 기본 헬스체크

```
GET /api/v1/health
```

#### 응답 예시

```json
{
  "status": "healthy",
  "timestamp": "2023-12-20T10:30:00Z"
}
```

### 9.2 상세 헬스체크

```
GET /api/v1/health/detail
```

#### 응답 예시

```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "faiss_index": {
      "status": "healthy",
      "vector_count": 500000,
      "index_size_mb": 1500
    },
    "embedding_model": {
      "status": "healthy",
      "model_name": "jhgan/ko-sroberta-multitask",
      "loaded": true
    }
  },
  "timestamp": "2023-12-20T10:30:00Z"
}
```

---

## 10. 관리자 API

### 10.1 ETL 수동 실행

```
POST /api/v1/admin/etl/run
```

#### 요청 본문

```json
{
  "job_type": "incremental",
  "target": "cases",
  "from_date": "2023-12-19"
}
```

### 10.2 인덱스 재빌드

```
POST /api/v1/admin/index/rebuild
```

#### 요청 본문

```json
{
  "target": "cases",
  "force": false
}
```

### 10.3 ETL 작업 상태 조회

```
GET /api/v1/admin/etl/status
```

#### 응답 예시

```json
{
  "success": true,
  "data": {
    "current_job": {
      "id": "job-12345",
      "type": "incremental",
      "status": "running",
      "progress": 45,
      "started_at": "2023-12-20T02:00:00Z"
    },
    "last_completed": {
      "id": "job-12344",
      "type": "incremental",
      "status": "success",
      "total_processed": 150,
      "finished_at": "2023-12-19T02:30:00Z"
    }
  }
}
```

---

## 11. SSR 페이지 라우트

### 11.1 페이지 목록

| 경로 | 설명 | 템플릿 |
|------|------|--------|
| `/` | 메인 (검색) 페이지 | index.html |
| `/search` | 검색 결과 페이지 | search.html |
| `/cases/{id}` | 판례 상세 페이지 | case_detail.html |
| `/similar` | 유사 판례 검색 페이지 | similar.html |
| `/constitutional/{id}` | 헌재결정례 상세 | constitutional_detail.html |
| `/about` | 서비스 소개 | about.html |

---

## 12. API 스키마 (Pydantic)

### 12.1 검색 요청 스키마

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=500, description="검색어")
    court: Optional[List[str]] = Field(None, description="법원 필터")
    case_type: Optional[str] = Field(None, description="사건유형")
    from_date: Optional[date] = Field(None, description="시작일")
    to_date: Optional[date] = Field(None, description="종료일")
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(20, ge=1, le=100, description="페이지 크기")
    sort: str = Field("relevance", description="정렬 기준")

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=10, max_length=2000, description="검색 질의")
    top_k: int = Field(10, ge=1, le=100, description="반환 결과 수")
    threshold: float = Field(0.3, ge=0, le=1, description="최소 유사도")
    filters: Optional[dict] = Field(None, description="필터 조건")
```

### 12.2 응답 스키마

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional
from datetime import datetime

T = TypeVar('T')

class PaginationMeta(BaseModel):
    total: int
    page: int
    size: int
    total_pages: int

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    meta: Optional[PaginationMeta] = None

class CaseListItem(BaseModel):
    id: int
    serial_number: str
    case_name: str
    case_number: str
    decision_date: date
    court_name: str
    case_type: str
    judgment_type: Optional[str]
    holding_summary: Optional[str]
    relevance_score: Optional[float] = None
    similarity_score: Optional[float] = None

class CaseDetail(BaseModel):
    id: int
    serial_number: str
    case_name: str
    case_number: str
    decision_date: date
    decision_type: Optional[str]
    court_name: str
    case_type: str
    judgment_type: Optional[str]
    holding: Optional[str]
    summary: Optional[str]
    full_text: Optional[str]
    reference_articles: List[dict]
    reference_cases: List[dict]
    source_url: Optional[str]
    created_at: datetime
    updated_at: datetime
```

---

## 13. 에러 코드 정의

| 코드 | HTTP Status | 설명 |
|------|-------------|------|
| VALIDATION_ERROR | 422 | 입력값 유효성 검증 실패 |
| CASE_NOT_FOUND | 404 | 판례를 찾을 수 없음 |
| SEARCH_ERROR | 500 | 검색 처리 오류 |
| EMBEDDING_ERROR | 500 | 임베딩 생성 오류 |
| INDEX_ERROR | 500 | 벡터 인덱스 오류 |
| DATABASE_ERROR | 500 | 데이터베이스 오류 |
| EXTERNAL_API_ERROR | 502 | 외부 API 오류 |
| RATE_LIMIT_EXCEEDED | 429 | 요청 제한 초과 |

---

## 14. API 버전 관리

- 현재 버전: `v1`
- URL 경로에 버전 포함: `/api/v1/...`
- 하위 호환성 유지 원칙
- 주요 변경 시 새 버전 릴리스
