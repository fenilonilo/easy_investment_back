from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Substitua pelo seu usuário, senha e nome do banco de dados local
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:admin@host.docker.internal:5432/easy_finace"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependência para injetar o banco nos endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()