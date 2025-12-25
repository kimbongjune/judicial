# -*- coding: utf-8 -*-
"""_parse_external_page 직접 테스트"""
import sys
import time
sys.path.insert(0, '.')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from etl.clients.law_api import LawAPIClient

def main():
    case_id = 608687
    url = f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={case_id}&mode=0"
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"URL: {url}")
        driver.get(url)
        time.sleep(5)
        
        final_url = driver.current_url
        print(f"Final URL: {final_url}")
        
        html = driver.page_source
        print(f"HTML 길이: {len(html)} bytes")
        
        # LawAPIClient 인스턴스 생성해서 파싱 테스트
        client = LawAPIClient()
        result = client._parse_external_page(html, case_id)
        
        print(f"\n=== 파싱 결과 ===")
        for k, v in result.items():
            if v:
                val = str(v)[:200] if len(str(v)) > 200 else v
                print(f"{k}: {val}")
            else:
                print(f"{k}: (없음)")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
