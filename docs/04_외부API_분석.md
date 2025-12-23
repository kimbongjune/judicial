# 외부 API 분석 - 법제처 OpenAPI

## 1. 개요

본 문서는 법제처에서 제공하는 국가법령정보 공동활용 OpenAPI에 대한 상세 분석입니다.

**API 포털**: https://open.law.go.kr/

---

## 2. API 신청 및 인증

### 2.1 API 키 발급 절차

1. **회원가입**: https://open.law.go.kr/LSO/login.do 에서 회원가입
2. **서비스 신청**: OPEN API > OPEN API 신청 메뉴에서 필요한 서비스 신청
3. **승인 대기**: 법제처 담당자 승인 (보통 1~3일 소요)
4. **인증키 발급**: 마이페이지에서 발급된 OC(인증키) 확인

### 2.2 인증 방식

- **인증 파라미터**: `OC` (Organization Code)
- **인증 위치**: URL Query Parameter
- **호출 제한**: 일 10,000건 (기본), 필요시 증량 요청 가능

### 2.3 기본 요청 URL

```
# 목록 조회
http://www.law.go.kr/DRF/lawSearch.do?OC={인증키}&target={대상}&type={응답형식}

# 상세 조회
http://www.law.go.kr/DRF/lawService.do?OC={인증키}&target={대상}&type={응답형식}&ID={일련번호}
```

---

## 3. 구현 필요 API 목록

본 프로젝트에서 구현해야 하는 API 목록입니다.

| API | target | 용도 | 예상 데이터량 |
|-----|--------|------|--------------|
| 판례 목록 | `prec` | 판례 리스트 수집 | ~250,000건 |
| 판례 본문 | `prec` | 판례 상세 수집 | ~250,000건 |
| 헌재결정례 목록 | `detc` | 헌재 결정례 리스트 | ~10,000건 |
| 헌재결정례 본문 | `detc` | 헌재 결정례 상세 | ~10,000건 |
| 법령해석례 목록 | `expc` | 법령해석 리스트 | ~50,000건 |
| 법령해석례 본문 | `expc` | 법령해석 상세 | ~50,000건 |

---

## 4. 판례 API

### 4.1 판례 목록 조회 API

#### 엔드포인트

```
GET http://www.law.go.kr/DRF/lawSearch.do
```

#### 요청 파라미터

| 파라미터 | 필수 | 타입 | 설명 | 예시 |
|----------|------|------|------|------|
| OC | ✅ | String | 인증키 | abc123 |
| target | ✅ | String | 대상 유형 | `prec` |
| type | ✅ | String | 응답 형식 | `XML` 또는 `JSON` |
| query | | String | 검색어 (사건명, 판결요지 등) | 손해배상 |
| display | | Integer | 페이지당 건수 (기본 20, 최대 100) | 100 |
| page | | Integer | 페이지 번호 (1부터 시작) | 1 |
| sort | | String | 정렬 기준 | `ddes` (선고일 내림차순) |
| curt | | String | 법원 코드 | 400201 (대법원) |
| caseNm | | String | 사건번호 검색 | 2023다 |
| caseTy | | String | 사건 유형 코드 | 400101 (민사) |
| fromDt | | String | 검색 시작일 (YYYYMMDD) | 20230101 |
| toDt | | String | 검색 종료일 (YYYYMMDD) | 20231231 |

#### 법원 코드

| 코드 | 법원명 |
|------|--------|
| 400201 | 대법원 |
| 400202 | 고등법원 |
| 400203 | 지방법원 |
| 400204 | 특허법원 |
| 400205 | 가정법원 |
| 400206 | 행정법원 |
| 400207 | 회생법원 |

#### 사건 유형 코드

| 코드 | 유형명 |
|------|--------|
| 400101 | 민사 |
| 400102 | 형사 |
| 400103 | 행정 |
| 400104 | 가사 |
| 400105 | 특허 |
| 400106 | 세무 |

#### 요청 예시

```bash
# 전체 판례 목록 (최신순, 100건)
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=prec&type=XML&display=100&page=1&sort=ddes"

# 키워드 검색
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=prec&type=XML&query=손해배상&display=100"

# 대법원 판례만
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=prec&type=XML&curt=400201&display=100"

# 기간 지정 검색
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=prec&type=XML&fromDt=20230101&toDt=20231231"

# 민사 사건만
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=prec&type=XML&caseTy=400101"
```

#### 응답 예시 (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PrecSearch>
    <totalCnt>156789</totalCnt>
    <page>1</page>
    <prec>
        <판례일련번호>123456</판례일련번호>
        <사건명>손해배상(기)</사건명>
        <사건번호>2023다12345</사건번호>
        <선고일자>20231215</선고일자>
        <선고>선고</선고>
        <법원명>대법원</법원명>
        <법원종류코드>400201</법원종류코드>
        <사건종류명>민사</사건종류명>
        <사건종류코드>400101</사건종류코드>
        <판결유형>판결</판결유형>
        <판시사항>불법행위로 인한 손해배상청구에서...</판시사항>
        <판결요지>불법행위로 인한 손해배상책임이 성립하려면...</판결요지>
        <참조조문>민법 제750조</참조조문>
        <참조판례>대법원 2020. 1. 1. 선고 2019다12345 판결</참조판례>
    </prec>
</PrecSearch>
```

#### 응답 필드

| 필드명 | 타입 | 설명 | DB 매핑 |
|--------|------|------|---------|
| totalCnt | Integer | 전체 검색 결과 건수 | - |
| page | Integer | 현재 페이지 번호 | - |
| 판례일련번호 | String | 법제처 고유 ID | `cases.serial_number` |
| 사건명 | String | 사건의 명칭 | `cases.case_name` |
| 사건번호 | String | 법원 사건번호 | `cases.case_number` |
| 선고일자 | String | 선고일 (YYYYMMDD) | `cases.decision_date` |
| 선고 | String | 선고/결정 | `cases.decision_type` |
| 법원명 | String | 판결 법원명 | `courts.name` |
| 법원종류코드 | String | 법원 유형 코드 | `courts.code` |
| 사건종류명 | String | 사건 분류명 | `case_types.name` |
| 사건종류코드 | String | 사건 분류 코드 | `case_types.code` |
| 판결유형 | String | 판결/결정/명령 | `cases.judgment_type` |
| 판시사항 | String | 핵심 판시사항 | `cases.holding` |
| 판결요지 | String | 판결 요약 | `cases.summary` |
| 참조조문 | String | 관련 법령 조문 | `cases.reference_articles_raw` |
| 참조판례 | String | 인용된 다른 판례 | `cases.reference_cases_raw` |

---

### 4.2 판례 본문 조회 API

#### 엔드포인트

```
GET http://www.law.go.kr/DRF/lawService.do
```

#### 요청 파라미터

| 파라미터 | 필수 | 타입 | 설명 | 예시 |
|----------|------|------|------|------|
| OC | ✅ | String | 인증키 | abc123 |
| target | ✅ | String | 대상 유형 | `prec` |
| type | ✅ | String | 응답 형식 | `XML` |
| ID | ✅ | String | 판례일련번호 | 123456 |

#### 요청 예시

```bash
curl "http://www.law.go.kr/DRF/lawService.do?OC={API_KEY}&target=prec&type=XML&ID=123456"
```

#### 응답 예시 (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PrecService>
    <판례정보일련번호>123456</판례정보일련번호>
    <사건명>손해배상(기)</사건명>
    <사건번호>2023다12345</사건번호>
    <선고일자>20231215</선고일자>
    <선고>선고</선고>
    <법원명>대법원</법원명>
    <법원종류코드>400201</법원종류코드>
    <사건종류명>민사</사건종류명>
    <사건종류코드>400101</사건종류코드>
    <판결유형>판결</판결유형>
    <판시사항>
        [1] 불법행위로 인한 손해배상청구에서 귀책사유의 존재...
        [2] 위자료 산정의 기준...
    </판시사항>
    <판결요지>
        [1] 불법행위로 인한 손해배상책임이 성립하려면 가해행위의 위법성,
        가해자의 고의 또는 과실, 피해자의 손해 발생 및 가해행위와
        손해 사이의 인과관계가 있어야 한다...
        [2] 위자료의 액수는 피해자의 나이, 직업, 사회적 지위...
    </판결요지>
    <참조조문>
        민법 제750조(불법행위의 내용)
        민법 제751조(재산 이외의 손해의 배상)
    </참조조문>
    <참조판례>
        대법원 2020. 1. 1. 선고 2019다12345 판결(공2020상, 123)
    </참조판례>
    <판례내용>
        【원고, 피상고인】 원고 (소송대리인 변호사 ○○○)
        【피고, 상고인】 피고 (소송대리인 법무법인 △△△)
        【원심판결】 서울고등법원 2023. 10. 1. 선고 2023나12345 판결
        【주문】
        상고를 기각한다.
        상고비용은 피고가 부담한다.
        【이유】
        상고이유를 판단한다.
        1. 불법행위의 성립에 관하여
        원심은 그 채택 증거들에 의하여 다음과 같은 사실을 인정하였다.
        ... (전문)
    </판례내용>
</PrecService>
```

#### 응답 필드 (목록 조회 대비 추가 필드)

| 필드명 | 타입 | 설명 | DB 매핑 |
|--------|------|------|---------|
| 판례내용 | String | 판결문 전문 | `cases.full_text` |

---

## 5. 헌재결정례 API

### 5.1 헌재결정례 목록 조회 API

#### 엔드포인트

```
GET http://www.law.go.kr/DRF/lawSearch.do
```

#### 요청 파라미터

| 파라미터 | 필수 | 타입 | 설명 | 예시 |
|----------|------|------|------|------|
| OC | ✅ | String | 인증키 | abc123 |
| target | ✅ | String | 대상 유형 | `detc` |
| type | ✅ | String | 응답 형식 | `XML` |
| query | | String | 검색어 | 위헌 |
| display | | Integer | 페이지당 건수 (최대 100) | 100 |
| page | | Integer | 페이지 번호 | 1 |
| sort | | String | 정렬 | `ddes` |
| fromDt | | String | 검색 시작일 | 20230101 |
| toDt | | String | 검색 종료일 | 20231231 |

#### 요청 예시

```bash
# 전체 헌재결정례 목록
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=detc&type=XML&display=100&page=1&sort=ddes"

# 키워드 검색
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=detc&type=XML&query=위헌&display=100"

# 기간 검색
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=detc&type=XML&fromDt=20230101&toDt=20231231"
```

#### 응답 예시 (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<DetcSearch>
    <totalCnt>8500</totalCnt>
    <page>1</page>
    <detc>
        <결정례일련번호>54321</결정례일련번호>
        <사건명>구 소득세법 제97조 제1항 제1호 등 위헌소원</사건명>
        <사건번호>2022헌바123</사건번호>
        <선고일자>20231130</선고일자>
        <결정유형>위헌</결정유형>
        <결정종류>헌법소원</결정종류>
        <결정요지>구 소득세법 제97조 제1항 제1호는 양도소득세의 
        필요경비 산입 범위를 지나치게 제한하여 재산권을 침해한다...</결정요지>
        <참조조문>헌법 제23조, 소득세법 제97조</참조조문>
        <참조판례>헌재 2020. 5. 27. 2018헌바456</참조판례>
    </detc>
</DetcSearch>
```

#### 응답 필드

| 필드명 | 타입 | 설명 | DB 매핑 |
|--------|------|------|---------|
| totalCnt | Integer | 전체 검색 결과 건수 | - |
| page | Integer | 현재 페이지 번호 | - |
| 결정례일련번호 | String | 법제처 고유 ID | `constitutional_decisions.serial_number` |
| 사건명 | String | 사건 명칭 | `constitutional_decisions.case_name` |
| 사건번호 | String | 헌재 사건번호 | `constitutional_decisions.case_number` |
| 선고일자 | String | 선고일 (YYYYMMDD) | `constitutional_decisions.decision_date` |
| 결정유형 | String | 위헌/합헌/각하 등 | `constitutional_decisions.decision_type` |
| 결정종류 | String | 헌법소원/위헌심판 등 | `constitutional_decisions.decision_category` |
| 결정요지 | String | 결정 요약 | `constitutional_decisions.summary` |
| 참조조문 | String | 관련 법령 조문 | `constitutional_decisions.reference_articles_raw` |
| 참조판례 | String | 관련 다른 결정례 | `constitutional_decisions.reference_cases_raw` |

---

### 5.2 헌재결정례 본문 조회 API

#### 엔드포인트

```
GET http://www.law.go.kr/DRF/lawService.do
```

#### 요청 파라미터

| 파라미터 | 필수 | 타입 | 설명 | 예시 |
|----------|------|------|------|------|
| OC | ✅ | String | 인증키 | abc123 |
| target | ✅ | String | 대상 유형 | `detc` |
| type | ✅ | String | 응답 형식 | `XML` |
| ID | ✅ | String | 결정례일련번호 | 54321 |

#### 요청 예시

```bash
curl "http://www.law.go.kr/DRF/lawService.do?OC={API_KEY}&target=detc&type=XML&ID=54321"
```

#### 응답 예시 (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<DetcService>
    <결정례정보일련번호>54321</결정례정보일련번호>
    <사건명>구 소득세법 제97조 제1항 제1호 등 위헌소원</사건명>
    <사건번호>2022헌바123</사건번호>
    <선고일자>20231130</선고일자>
    <결정유형>위헌</결정유형>
    <결정종류>헌법소원</결정종류>
    <주문>구 소득세법(2020. 12. 29. 법률 제17757호로 개정되고, 
    2021. 12. 21. 법률 제18584호로 개정되기 전의 것) 제97조 
    제1항 제1호 중 '양도자산의 취득에 든 실지거래가액'에 관한 
    부분은 헌법에 위반된다.</주문>
    <이유>
        1. 사건개요
        청구인은 2018년 부동산을 양도하면서 양도소득세를 신고하였다...
        
        2. 심판대상
        이 사건 심판대상은 구 소득세법 제97조 제1항 제1호...
        
        3. 청구인의 주장
        양도소득세 계산시 필요경비에 실질적인 취득비용을...
        
        4. 판단
        가. 재산권 침해 여부
        (1) 양도소득세는 자산의 양도로 인하여 발생한 소득에 대하여...
        
        5. 결론
        구 소득세법 제97조 제1항 제1호는 헌법에 위반된다.
    </이유>
    <결정요지>구 소득세법 제97조 제1항 제1호는 양도소득세의 
    필요경비 산입 범위를 지나치게 제한하여 재산권을 침해한다...</결정요지>
    <참조조문>헌법 제23조, 소득세법 제97조</참조조문>
    <참조판례>헌재 2020. 5. 27. 2018헌바456</참조판례>
</DetcService>
```

#### 응답 필드 (목록 조회 대비 추가 필드)

| 필드명 | 타입 | 설명 | DB 매핑 |
|--------|------|------|---------|
| 주문 | String | 결정 주문 | `constitutional_decisions.ruling` |
| 이유 | String | 결정 이유 전문 | `constitutional_decisions.full_text` |

---

## 6. 법령해석례 API

### 6.1 법령해석례 목록 조회 API

#### 엔드포인트

```
GET http://www.law.go.kr/DRF/lawSearch.do
```

#### 요청 파라미터

| 파라미터 | 필수 | 타입 | 설명 | 예시 |
|----------|------|------|------|------|
| OC | ✅ | String | 인증키 | abc123 |
| target | ✅ | String | 대상 유형 | `expc` |
| type | ✅ | String | 응답 형식 | `XML` |
| query | | String | 검색어 | 계약 |
| display | | Integer | 페이지당 건수 (최대 100) | 100 |
| page | | Integer | 페이지 번호 | 1 |
| sort | | String | 정렬 | `ddes` |
| fromDt | | String | 검색 시작일 | 20230101 |
| toDt | | String | 검색 종료일 | 20231231 |

#### 요청 예시

```bash
# 전체 법령해석례 목록
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=expc&type=XML&display=100&page=1&sort=ddes"

# 키워드 검색
curl "http://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=expc&type=XML&query=계약&display=100"
```

#### 응답 예시 (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExpcSearch>
    <totalCnt>45000</totalCnt>
    <page>1</page>
    <expc>
        <해석례일련번호>98765</해석례일련번호>
        <안건명>민법 제750조의 적용 범위에 관한 해석</안건명>
        <안건번호>법제처-23-0001</안건번호>
        <회신일자>20231215</회신일자>
        <소관기관>법무부</소관기관>
        <질의기관>서울특별시</질의기관>
        <질의요지>민법 제750조에서 정한 '불법행위'의 범위에 
        행정기관의 직무행위가 포함되는지 여부</질의요지>
        <회답>민법 제750조에서 정한 불법행위에는 행정기관의 
        직무행위도 포함될 수 있으나, 국가배상법이 적용되는 
        경우에는 그 법률이 우선 적용됩니다.</회답>
        <이유>민법 제750조는 고의 또는 과실로 인한 위법행위로 
        타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다고 
        규정하고 있습니다...</이유>
        <참조조문>민법 제750조, 국가배상법 제2조</참조조문>
    </expc>
</ExpcSearch>
```

#### 응답 필드

| 필드명 | 타입 | 설명 | DB 매핑 |
|--------|------|------|---------|
| totalCnt | Integer | 전체 검색 결과 건수 | - |
| page | Integer | 현재 페이지 번호 | - |
| 해석례일련번호 | String | 법제처 고유 ID | `legal_interpretations.serial_number` |
| 안건명 | String | 안건 명칭 | `legal_interpretations.case_name` |
| 안건번호 | String | 안건 번호 | `legal_interpretations.case_number` |
| 회신일자 | String | 회신일 (YYYYMMDD) | `legal_interpretations.response_date` |
| 소관기관 | String | 법률 소관 기관 | `legal_interpretations.competent_agency` |
| 질의기관 | String | 질의한 기관 | `legal_interpretations.inquiry_agency` |
| 질의요지 | String | 질의 내용 요약 | `legal_interpretations.inquiry_summary` |
| 회답 | String | 법제처 회답 | `legal_interpretations.response` |
| 이유 | String | 회답 이유 | `legal_interpretations.reasoning` |
| 참조조문 | String | 관련 법령 조문 | `legal_interpretations.reference_articles_raw` |

---

### 6.2 법령해석례 본문 조회 API

#### 엔드포인트

```
GET http://www.law.go.kr/DRF/lawService.do
```

#### 요청 파라미터

| 파라미터 | 필수 | 타입 | 설명 | 예시 |
|----------|------|------|------|------|
| OC | ✅ | String | 인증키 | abc123 |
| target | ✅ | String | 대상 유형 | `expc` |
| type | ✅ | String | 응답 형식 | `XML` |
| ID | ✅ | String | 해석례일련번호 | 98765 |

#### 요청 예시

```bash
curl "http://www.law.go.kr/DRF/lawService.do?OC={API_KEY}&target=expc&type=XML&ID=98765"
```

#### 응답 예시 (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExpcService>
    <해석례정보일련번호>98765</해석례정보일련번호>
    <안건명>민법 제750조의 적용 범위에 관한 해석</안건명>
    <안건번호>법제처-23-0001</안건번호>
    <회신일자>20231215</회신일자>
    <소관기관>법무부</소관기관>
    <질의기관>서울특별시</질의기관>
    <질의요지>민법 제750조에서 정한 '불법행위'의 범위에 
    행정기관의 직무행위가 포함되는지 여부</질의요지>
    <회답>민법 제750조에서 정한 불법행위에는 행정기관의 
    직무행위도 포함될 수 있으나, 국가배상법이 적용되는 
    경우에는 그 법률이 우선 적용됩니다.</회답>
    <이유>
        1. 질의 배경
        서울특별시에서는 소속 공무원의 직무상 행위로 인하여 
        시민에게 손해가 발생한 경우의 법적 책임에 관하여 질의함.
        
        2. 관계 법령
        가. 민법 제750조
        고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 
        자는 그 손해를 배상할 책임이 있다.
        
        나. 국가배상법 제2조
        국가나 지방자치단체는 공무원 또는 공무를 위탁받은 사인이 
        직무를 집행하면서 고의 또는 과실로 법령을 위반하여 
        타인에게 손해를 입힌 때에는 이 법에 따라 그 손해를 
        배상하여야 한다.
        
        3. 검토 의견
        민법 제750조는 불법행위에 대한 일반적 손해배상책임을 
        규정한 것으로...
        
        4. 결론
        따라서 민법 제750조의 불법행위에는 행정기관의 직무행위도 
        포함될 수 있으나...
    </이유>
    <참조조문>민법 제750조, 국가배상법 제2조</참조조문>
</ExpcService>
```

#### 응답 필드 (목록 조회와 동일, 이유 필드가 더 상세)

| 필드명 | 타입 | 설명 | DB 매핑 |
|--------|------|------|---------|
| 이유 | String | 상세 회답 이유 (전문) | `legal_interpretations.full_reasoning` |

---

## 7. API 호출 제한 및 에러 처리

### 7.1 호출 제한

| 항목 | 제한 |
|------|------|
| 일일 호출 제한 | 10,000건 (기본) |
| 초당 호출 제한 | 10건 |
| 페이지당 최대 건수 | 100건 |
| 응답 시간 제한 | 30초 |

### 7.2 에러 코드

| 에러 코드 | 설명 | 대응 방안 |
|-----------|------|-----------|
| -1 | 인증 실패 | OC 키 확인 |
| -2 | 필수 파라미터 누락 | 요청 파라미터 확인 |
| -3 | 잘못된 파라미터 값 | 파라미터 형식 확인 |
| -4 | 호출 제한 초과 | 대기 후 재시도 |
| -5 | 서비스 점검 중 | 나중에 재시도 |
| -99 | 시스템 오류 | 법제처 문의 |

### 7.3 에러 응답 예시

```xml
<?xml version="1.0" encoding="UTF-8"?>
<error>
    <code>-1</code>
    <message>인증에 실패하였습니다.</message>
</error>
```

### 7.4 에러 처리 코드

```python
import aiohttp
import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def call_law_api(
    endpoint: str,
    params: dict,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> Optional[str]:
    """법제처 API 호출 (재시도 포함)"""
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        # 에러 응답 확인
                        if "<error>" in text:
                            logger.error(f"API Error: {text}")
                            return None
                        return text
                    elif response.status == 429:  # Rate limit
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        logger.error(f"HTTP Error: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise
    
    return None
```

---

## 8. ETL 시나리오별 API 사용

### 8.1 초기 전체 데이터 수집

```python
async def collect_all_data():
    """전체 데이터 수집 (초기)"""
    
    # 1. 판례 수집
    await collect_precedents()
    
    # 2. 헌재결정례 수집
    await collect_constitutional_decisions()
    
    # 3. 법령해석례 수집
    await collect_legal_interpretations()

async def collect_precedents():
    """판례 전체 수집"""
    page = 1
    while True:
        params = {
            "OC": API_KEY,
            "target": "prec",
            "type": "XML",
            "display": 100,
            "page": page,
            "sort": "ddes"
        }
        
        response = await call_law_api(LIST_ENDPOINT, params)
        cases = parse_case_list(response)
        
        if not cases:
            break
        
        for case in cases:
            # 본문 조회
            detail = await get_case_detail(case["serial_number"])
            await save_case(detail)
            await asyncio.sleep(0.1)  # Rate limiting
        
        page += 1

async def collect_constitutional_decisions():
    """헌재결정례 전체 수집"""
    page = 1
    while True:
        params = {
            "OC": API_KEY,
            "target": "detc",
            "type": "XML",
            "display": 100,
            "page": page,
            "sort": "ddes"
        }
        
        response = await call_law_api(LIST_ENDPOINT, params)
        decisions = parse_constitutional_list(response)
        
        if not decisions:
            break
        
        for decision in decisions:
            detail = await get_constitutional_detail(decision["serial_number"])
            await save_constitutional(detail)
            await asyncio.sleep(0.1)
        
        page += 1

async def collect_legal_interpretations():
    """법령해석례 전체 수집"""
    page = 1
    while True:
        params = {
            "OC": API_KEY,
            "target": "expc",
            "type": "XML",
            "display": 100,
            "page": page,
            "sort": "ddes"
        }
        
        response = await call_law_api(LIST_ENDPOINT, params)
        interpretations = parse_interpretation_list(response)
        
        if not interpretations:
            break
        
        for interp in interpretations:
            detail = await get_interpretation_detail(interp["serial_number"])
            await save_interpretation(detail)
            await asyncio.sleep(0.1)
        
        page += 1
```

### 8.2 일일 증분 동기화

```python
async def daily_sync(last_sync_date: str):
    """일일 증분 동기화"""
    
    # 판례 증분 동기화
    await sync_new_precedents(last_sync_date)
    
    # 헌재결정례 증분 동기화
    await sync_new_constitutional(last_sync_date)
    
    # 법령해석례 증분 동기화
    await sync_new_interpretations(last_sync_date)

async def sync_new_precedents(from_date: str):
    """신규 판례 동기화"""
    params = {
        "OC": API_KEY,
        "target": "prec",
        "type": "XML",
        "display": 100,
        "page": 1,
        "fromDt": from_date,
        "sort": "ddes"
    }
    # ... 수집 로직
```

---

## 9. 초기 데이터 수집 예상 시간

| 대상 | 건수 | API 호출 수 | 예상 시간 |
|------|------|------------|----------|
| 판례 | ~250,000건 | ~252,500회 | ~70시간 |
| 헌재결정례 | ~10,000건 | ~10,100회 | ~3시간 |
| 법령해석례 | ~50,000건 | ~50,500회 | ~14시간 |
| **합계** | **~310,000건** | **~313,000회** | **~87시간** |

> ⚠️ API 일일 제한(10,000건) 고려 시 약 32일 소요
> 호출 제한 증량 신청 시 단축 가능

---

## 10. 참고 링크

- **API 포털**: https://open.law.go.kr/
- **API 활용가이드**: https://open.law.go.kr/LSO/openApi/guideList.do
- **개발자 LAB**: https://open.law.go.kr/LSO/lab/hangulAddr.do
- **오류 자가진단**: https://open.law.go.kr/LSO/lab/selfDiagnosis.do
- **문의**: lawmanager@korea.kr, 02-2109-6446
