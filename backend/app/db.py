from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool, StaticPool

from .core.config import settings


def _get_connect_args() -> dict:
    """Get database-specific connection arguments with timeouts."""
    db_url = settings.database_url.lower()

    if "sqlite" in db_url:
        # SQLite: use timeout for busy waiting
        return {
            "timeout": settings.db_connect_timeout,
            "check_same_thread": False,
        }
    elif "postgresql" in db_url or "postgres" in db_url:
        # PostgreSQL: connection and statement timeouts
        return {
            "connect_timeout": settings.db_connect_timeout,
            "options": f"-c statement_timeout={settings.db_command_timeout * 1000}",  # PostgreSQL uses milliseconds
        }
    elif "mysql" in db_url:
        # MySQL: connection and read/write timeouts
        return {
            "connect_timeout": settings.db_connect_timeout,
            "read_timeout": settings.db_command_timeout,
            "write_timeout": settings.db_command_timeout,
        }
    else:
        return {}


def _get_pool_class():
    """Get appropriate pool class based on database type."""
    # SQLite requires StaticPool for in-memory databases or single-threaded access
    if "sqlite" in settings.database_url.lower() and ":memory:" in settings.database_url:
        return StaticPool
    return QueuePool


# Configure database engine with connection pooling and timeouts
# See: https://docs.sqlalchemy.org/en/20/core/pooling.html
engine = create_engine(
    settings.database_url,
    future=True,
    # Connection pooling configuration
    poolclass=_get_pool_class(),
    pool_size=settings.db_pool_size,  # Number of connections to keep open
    max_overflow=settings.db_max_overflow,  # Max additional connections beyond pool_size
    pool_timeout=settings.db_pool_timeout,  # Seconds to wait before giving up on getting a connection
    pool_recycle=settings.db_pool_recycle,  # Recycle connections after N seconds (prevents stale connections)
    pool_pre_ping=True,  # Verify connections before using them
    # Database-specific connection arguments (timeouts, etc.)
    connect_args=_get_connect_args(),
    # Echo SQL queries in dev mode (disabled in production for performance)
    echo=settings.app_env == "dev" and settings.database_url != "sqlite:///./regami.db",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
