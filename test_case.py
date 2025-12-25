# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
from etl.clients.law_api import LawAPIClient

test_cases = [
    '수원지방법원성남지원-2023-가합-402000 사해행위취소',
    '서울중앙지방법원-2024-가단-5506074',
    '대법원2025다210731 (2025.5.15)',
    '의정부지방법원남양주지원2023가단42925 (2025.2.18)',
]

import re
for case in test_cases:
    r = LawAPIClient.parse_case_title(case)
    is_valid = bool(re.match(r'^\d{4}[가-힣]+\d+$', r['case_number']))
    status = 'OK' if is_valid else 'FAIL'
    print(f'[{status}] {case[:50]:50s}')
    print(f'       court: {r["court_name"]}')
    print(f'       case:  {r["case_number"]}')
