# -*- coding: utf-8 -*-
"""608687 HTML 덤프 테스트"""
import asyncio
import sys
import time
sys.path.insert(0, '.')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

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
        time.sleep(5)  # 충분히 대기
        
        final_url = driver.current_url
        print(f"Final URL: {final_url}")
        
        html = driver.page_source
        print(f"HTML 길이: {len(html)} bytes")
        
        # HTML 파싱
        soup = BeautifulSoup(html, 'html.parser')
        
        # bo_body_cont 확인
        bo_body = soup.find('div', class_='bo_body_cont')
        print(f"\nbo_body_cont 존재: {bo_body is not None}")
        
        if bo_body:
            text = bo_body.get_text(separator='\n', strip=True)
            print(f"bo_body_cont 텍스트 길이: {len(text)}")
            print(f"\n--- 텍스트 시작 (처음 500자) ---")
            print(text[:500])
        else:
            print("\n--- 전체 body 텍스트 (처음 500자) ---")
            print(soup.get_text()[:500])
        
        # 주문, 이유 확인
        full_text = soup.get_text()
        print(f"\n'주문' 포함: {'주문' in full_text or '주 문' in full_text}")
        print(f"'이유' 포함: {'이유' in full_text or '이 유' in full_text}")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
