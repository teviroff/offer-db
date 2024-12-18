from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mongoengine import connect
from minio import Minio

from .models.base import Base, FileStream
from .models.auxillary.address import Country, City
# from models.auxillary.phone_number import PhoneNumber
from .models.user import (
    PersonalAPIKey, DeveloperAPIKey, APIKey, User, UserInfo, CV
)
from .models.opportunity.opportunity import (
    Opportunity, OpportunityProvider, OpportunityTag, OpportunityGeotag,
    OpportunityToTag, OpportunityToGeotag, OpportunityCard, OpportunityResponse,
)
from .models.opportunity.form import OpportunityForm

from . import config as cfg

def get_pg_engine(user: str, password: str, host: str, port: int, db_name: str):
    return create_engine(f'postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}')

def connect_mongo_db(user: str, password: str, host: str, port: int, db_name: str):
    connect(host=f'mongodb://{user}:{password}@{host}:{port}/{db_name}')

# TODO: figure out cerificates
def get_minio_client(access_key: str, secret_key: str, host: str, port: int):
    return Minio(f'{host}:{port}', access_key=access_key, secret_key=secret_key, secure=False)

# run 'setup/dbconfig.bat' if you don't have dbconfig.py
pg_engine = get_pg_engine(
    user=cfg.PG_USERNAME,
    password=cfg.PG_PASSWORD,
    host=cfg.PG_HOST,
    port=cfg.PG_PORT,
    db_name=cfg.PG_DB_NAME,
)
connect_mongo_db(
    user=cfg.MONGO_USERNAME,
    password=cfg.MONGO_PASSWORD,
    host=cfg.MONGO_HOST,
    port=cfg.MONGO_PORT,
    db_name=cfg.MONGO_DB_NAME,
)
minio_client = get_minio_client(
    access_key=cfg.MINIO_ACCESS_KEY,
    secret_key=cfg.MINIO_SECRET_KEY,
    host=cfg.MINIO_HOST,
    port=cfg.MINIO_PORT,
)

Session = sessionmaker(bind=pg_engine)
