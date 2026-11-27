import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from sqlalchemy.exc import IntegrityError

from migrations.bootstrap import bootstrap
from scripts.seed_demo import seed
from src.config.settings import SEED_DEMO
from src.middlewares.body_limit import BodyLimit
from src.middlewares.errors import data_conflict, invalid_data, missing_data
from src.middlewares.request_id import request_id
from src.routes import auth, datasets, runs, system


@asynccontextmanager
async def lifespan(_):
    bootstrap()
    if SEED_DEMO:
        try:
            seed()
        except Exception:
            logging.getLogger(__name__).exception('演示数据初始化失败')
    yield


app = FastAPI(title='yangyang-zipper-select', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url='/api/openapi.json')
app.add_middleware(BodyLimit)
app.middleware('http')(request_id)
app.add_exception_handler(ValueError, invalid_data)
app.add_exception_handler(LookupError, missing_data)
app.add_exception_handler(IntegrityError, data_conflict)
api = APIRouter(prefix='/api')
for module in (system, auth, datasets, runs):
    api.include_router(module.router)
app.include_router(api)
