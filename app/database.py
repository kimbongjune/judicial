"""
데이터베이스 연결 및 세션 관리
SQLAlchemy 비동기 엔진 사용
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# 비동기 엔진 생성
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

# 세션 팩토리
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 모델 베이스 클래스"""
    pass


async def init_db():
    """데이터베이스 테이블 초기화"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """데이터베이스 테이블 삭제"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_session() -> AsyncSession:
    """의존성 주입용 세션 생성기"""
    async with async_session_maker() as session:
        yield session
