from fastapi import Depends
from starlette.config import Config
from sqlmodel import create_engine,Session
from typing import Annotated

config = Config(".env")
db:str = config("DATABASE_URL",cast=str)
connection_string:str = db.replace("postgresql","postgresql+psycopg2")

sendername = config("SENDER_NAME")
senderemail = config("SENDER_EMAIL")
SMTP_PASSWORD = config("SMTP_PASSWORD")
engine = create_engine(connection_string,pool_pre_ping=True , echo=True, pool_recycle=300,max_overflow=0)

def get_session():
    with Session(engine) as session:
        yield session

DB_SESSION= Annotated[Session,Depends(get_session)]