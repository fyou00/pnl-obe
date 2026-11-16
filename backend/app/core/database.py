from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DatabaseSettings


class Database:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.engine = create_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3, "options": "-c timezone=UTC"},
        )
        self.session_factory = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False
        )

    def dispose(self) -> None:
        self.engine.dispose()
