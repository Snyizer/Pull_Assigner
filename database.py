from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schem import Base

# Создаём движок SQLite
SQLITE_DATABASE_URL = "sqlite:///teams.db"

engine = create_engine(
    SQLITE_DATABASE_URL,
    connect_args={"check_same_thread": False}  #
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ База данных инициализирована!")
