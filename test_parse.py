# -*- coding: utf-8 -*-
"""사건번호 파싱 테스트"""
import re
import sys
sys.path.insert(0, '.')

from etl.clients.law_api import LawAPIClient

test_cases = [
    '대법원2025다210731 (2025.5.15)',
    '수원지방법원-2024나70449',
    '서울중앙지방법원-2024-가단-5506074(2025.5.13.)',
    '서울중앙지방법원-2024-구합-63395(2025.5.1.)',
    '수원지방법원 안양지원-2023가단-105196',
    '춘천지방법원-2025구합-30095',
    '제주지방법원-2024-가합-12350(2025.4.24.)',
    '춘천지방법원-20274-구합*318',
    '대법원-2024-다-319673(2025.3.13.)',
    '수원지방법원 안산지원-2024-가단-90439(2025.3.12.)',
    '서울중앙지방법원2024가단5254618 (2025. 2. 26)',
    '의정부지방법원남양주지원2023가단42925 (2025.2.18)',
]

print('='*70)
print('사건번호 파싱 테스트')
print('='*70)

success = 0
for case in test_cases:
    r = LawAPIClient.parse_case_title(case)
    is_valid = bool(re.match(r'^\d{4}[가-힣]+\d+$', r['case_number']))
    status = 'OK' if is_valid else 'FAIL'
    if is_valid:
        success += 1
    court = r['court_name'][:25] if r['court_name'] else ''
    print(f'[{status}] {case[:40]:40s} -> court: {court:25s} case: {r["case_number"]}')

print('='*70)
print(f'결과: {success}/{len(test_cases)} 성공')
