"""
ETL 병렬 처리 유틸리티

Selenium 및 API 호출의 병렬 처리를 위한 유틸리티 모듈
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable, Any, TypeVar, Optional
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

# 전역 ThreadPoolExecutor (Selenium 등 동기 작업용)
_executor: Optional[ThreadPoolExecutor] = None


def get_executor(max_workers: int = 5) -> ThreadPoolExecutor:
    """전역 ThreadPoolExecutor 반환 (싱글톤)"""
    global _executor
    if _executor is None or _executor._shutdown:
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


def shutdown_executor():
    """전역 ThreadPoolExecutor 종료"""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None


async def run_in_thread(func: Callable[..., T], *args, **kwargs) -> T:
    """
    동기 함수를 ThreadPoolExecutor에서 비동기로 실행
    
    Args:
        func: 실행할 동기 함수
        *args: 함수 인자
        **kwargs: 함수 키워드 인자
        
    Returns:
        함수 실행 결과
    """
    loop = asyncio.get_event_loop()
    executor = get_executor()
    
    # kwargs를 처리하기 위한 래퍼
    def wrapper():
        return func(*args, **kwargs)
    
    return await loop.run_in_executor(executor, wrapper)


async def process_batch(
    items: List[Any],
    processor: Callable[[Any], Any],
    concurrency: int = 5,
    return_exceptions: bool = True
) -> List[Any]:
    """
    아이템 리스트를 병렬로 처리
    
    Args:
        items: 처리할 아이템 리스트
        processor: 각 아이템을 처리하는 비동기 함수
        concurrency: 동시 처리 개수
        return_exceptions: True면 예외도 결과에 포함
        
    Returns:
        처리 결과 리스트 (순서 보장)
    """
    semaphore = asyncio.Semaphore(concurrency)
    
    async def process_with_semaphore(item):
        async with semaphore:
            return await processor(item)
    
    tasks = [process_with_semaphore(item) for item in items]
    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)


class BatchProcessor:
    """배치 단위 병렬 처리기"""
    
    def __init__(self, concurrency: int = 5):
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self._processed = 0
        self._errors = 0
    
    async def process(
        self,
        items: List[Any],
        processor: Callable[[Any], Any],
    ) -> List[Any]:
        """
        아이템 리스트를 병렬로 처리
        
        Args:
            items: 처리할 아이템 리스트
            processor: 각 아이템을 처리하는 비동기 함수
            
        Returns:
            처리 결과 리스트
        """
        async def process_with_semaphore(item):
            async with self.semaphore:
                try:
                    result = await processor(item)
                    self._processed += 1
                    return result
                except Exception as e:
                    self._errors += 1
                    logger.error(f"처리 실패: {e}")
                    return e
        
        tasks = [process_with_semaphore(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    @property
    def stats(self) -> dict:
        return {
            "processed": self._processed,
            "errors": self._errors
        }
