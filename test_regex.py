import re

def parse_case_title(title: str):
    """사건번호에서 법원명과 사건번호 추출"""
    if not title:
        return {"court_name": "", "case_number": ""}
    
    # 법원/지원 패턴
    court_pattern = r'(?:법원|대법원|지원)(?:\([^)]+\))?'
    
    # 패턴 1: "법원명-년도-종류-번호" 형식
    pattern1 = rf'^(.+?{court_pattern})-(\d{{4}})-([가-힣]+)-(\d+)$'
    match = re.match(pattern1, title)
    if match:
        return {"court_name": match.group(1), "case_number": f"{match.group(2)}{match.group(3)}{match.group(4)}"}
    
    # 패턴 2: "법원명년도종류번호" 형식 (붙어있음)
    pattern2 = rf'^(.+?{court_pattern})(\d{{4}})([가-힣]+)(\d+)$'
    match = re.match(pattern2, title)
    if match:
        return {"court_name": match.group(1), "case_number": f"{match.group(2)}{match.group(3)}{match.group(4)}"}
    
    # 패턴 3: 순수 사건번호만
    pattern3 = r'^(\d{2,4})([가-힣]+)(\d+)$'
    match = re.match(pattern3, title)
    if match:
        return {"court_name": "", "case_number": title}
    
    return {"court_name": "", "case_number": title}

test_cases = [
    # 이미지 1 - 법원/지원 하이픈 형식
    "서울고등법원(인천)-2025-누-10220",
    "원주지원-2023-가단-59850",
    "안양지원-2025-가-103549",
    "부천지원-2025-가단-104554",
    # 이미지 1 - 법원 붙어있는 형식
    "출중앙지방법원2025가단98622",
    "서울고등법원2025누6453",
    "대전고등법원2025누385",
    # 이미지 1 - 순수 사건번호
    "2024구합92890",
    "2024구합73547",
    "2025누670",
    "2021다252977",
    "2024드20898",
    "2025다212444",
    "2025두34430",
    "2025드36",
    "2025두34697",
    "2025두34660",
    "2022드10369",
    "2024구단15644",
    "2021다225074",
    "2025드9446",
    "2024드19539",
    "2025가단108658",
    "2025두33647",
    "2025고단1523",
    "2025구단4275",
    "2025구합50528",
    "2024누73686",
    "2024구합22077",
    "2023구합65397",
    "2025누6398",
    "2024가소9129",
    "2024누57158",
    "2024누72744",
    "2025가단212776",
    "2024누63023",
    # 이미지 2 - 법원/지원 하이픈 형식
    "광주고등법원(전주)-2024-누-1066",
    "평택지원-2025-가단-53224",
    "광주고등법원(전주)-2024-누-834",
    "안양지원-2024-가단-130342",
    # 이미지 2 - 순수 사건번호
    "2024구합23094",
    "2024구합20132",
    "2022가단32165",
    "2024누71543",
    "2024누14452",
    "2024누64415",
    "2024누66657",
    "2023구합88726",
    "2024구합93565",
    "2020구합70700",
    "2024구합66489",
    "2025구합50557",
    "2023구합7196",
]

print("=" * 80)
print("사건번호 파싱 테스트 - 총 %d건" % len(test_cases))
print("=" * 80)

success = 0
fail = 0
for title in test_cases:
    r = parse_case_title(title)
    # 법원명이 파싱되었거나, 순수 사건번호인 경우 성공
    is_pure_case = re.match(r'^(\d{2,4})([가-힣]+)(\d+)$', title)
    if r['court_name'] or is_pure_case:
        status = "OK"
        success += 1
    else:
        status = "FAIL"
        fail += 1
    print(f"[{status}] '{title}' -> court:'{r['court_name']}', case:'{r['case_number']}'")

print("=" * 80)
print(f"결과: 성공 {success}건, 실패 {fail}건")

