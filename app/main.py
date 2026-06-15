from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from app.database import engine, Base
from app.routers import projects, passages, collation, export, resolution, kgraph, transmission

Base.metadata.create_all(bind=engine)

app = FastAPI(title="古籍校勘比对系统")

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(projects.router, tags=["projects"])
app.include_router(passages.router, tags=["passages"])
app.include_router(collation.router, tags=["collation"])
app.include_router(export.router, tags=["export"])
app.include_router(resolution.router, tags=["resolution"])
app.include_router(kgraph.router, tags=["knowledge_graph"])
app.include_router(transmission.router, tags=["transmission_analysis"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "古籍校勘比对系统运行正常"}
