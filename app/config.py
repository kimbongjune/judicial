"""
법률 판례 검색 시스템 - 설정 모듈
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # 앱 설정
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "your-super-secret-key-change-in-production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # 법제처 API 설정
    law_api_oc: str = "nocdu112"
    law_api_base_url: str = "http://www.law.go.kr/DRF"
    law_api_rate_limit: int = 10000
    
    # 데이터베이스 설정
    database_url: str = "sqlite+aiosqlite:///./data/judicial.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # 임베딩 모델 설정
    embedding_model: str = "jhgan/ko-sroberta-multitask"
    embedding_batch_size: int = 32
    transformers_cache: str = "./data/cache/transformers"
    
    # FAISS 설정
    faiss_index_path: str = "./data/faiss"
    faiss_index_type: str = "flat"
    faiss_nlist: int = 100
    
    # 검색 설정
    default_search_limit: int = 20
    max_search_limit: int = 100
    similarity_threshold: float = 0.3
    
    # ETL 설정
    etl_batch_size: int = 100
    etl_request_delay: float = 0.5
    etl_max_retries: int = 3
    
    # 로깅 설정
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    log_max_size: int = 10
    log_backup_count: int = 5
    
    # CORS 설정
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """CORS 허용 오리진 목록"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
