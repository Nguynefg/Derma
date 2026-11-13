"""Application entry point: startup, middleware, routers and frontend hosting."""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from app.core.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / '.env', override=False)
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from PIL import Image
from app.database.connection import Base, engine
from app.core.responses import PublicJSONResponse
from app.database.migrations.numeric_ids import upgrade
from app.database.migrations.disease_name_index import ensure_name_index
from app.data.seed import seed
from app.data.library_expansion import seed_expansion
from app.data.library_extended import seed_extended
from app.data.library_dermnet import seed_dermnet
from app.data.library_general import seed_general
from app.modules.library.icd_import import process_pending_import
from app.modules.library.icd_merge import merge_icd_tables
from app.modules.library.icd_chapters import translate_chapter_titles
from app.modules.library.icd_translation import apply_translated_titles
from app.modules.library.documents import seed_documents
from app.core.middleware import BoundedBody, PublicCompression, safeguards
import app.modules.auth.routes as auth
import app.modules.library.routes as library
import app.modules.history.routes as history
import app.modules.images.routes as images
import app.modules.assistant.routes as knowledge
import app.modules.admin.routes as admin
import app.modules.library.icd_routes as icd
import app.modules.symptoms.routes as symptoms
import app.modules.profile.routes as profile

Image.MAX_IMAGE_PIXELS = 12_000_000


@asynccontextmanager
async def lifespan(_):
    result = upgrade(engine, PROJECT_ROOT / 'storage/backups', apply=True)
    logging.getLogger("uvicorn.error").info(
        "Database schema v2: %s; provider=%s; expected tables=%d",
        result["status"],
        engine.dialect.name,
        len(Base.metadata.tables),
    )
    if result.get("backup"):
        logging.getLogger("uvicorn.error").info("Database backup: %s", result["backup"])
    logging.getLogger("uvicorn.error").info("Disease name index: %s", ensure_name_index(engine))
    seed()
    seed_documents()
    seed_expansion()
    seed_extended()
    seed_dermnet()
    seed_general()
    if engine.dialect.name == "mssql":
        merged_icd = merge_icd_tables(
            engine, PROJECT_ROOT / 'storage/backups'
        )
        if merged_icd["status"] == "merged":
            logging.getLogger("uvicorn.error").info("ICD consolidation: %s", merged_icd)
    pending_icd = (
        process_pending_import(engine, PROJECT_ROOT / 'storage/imports/icd-import')
        if engine.dialect.name == "mssql"
        else None
    )
    if pending_icd:
        logging.getLogger("uvicorn.error").info("ICD import: %s", pending_icd)
    translated = translate_chapter_titles(engine)
    if translated["updated_chapters"]:
        logging.getLogger("uvicorn.error").info("ICD Vietnamese chapter titles: %s", translated)
    translated_titles = apply_translated_titles(engine)
    if translated_titles["updated_titles"]:
        logging.getLogger("uvicorn.error").info("ICD Vietnamese titles: %s", translated_titles)
    yield


app = FastAPI(
    title="Derma Library API",
    version="0.2.0",
    lifespan=lifespan,
    default_response_class=PublicJSONResponse,
)
@app.exception_handler(RequestValidationError)
async def invalid_request(_request, error):
    # Never reflect password fields, patient text or validator context in errors.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": item.get("loc", []), "type": item.get("type", "validation_error"),
         "msg": "Thông tin chưa hợp lệ. Vui lòng kiểm tra lại."}
        for item in error.errors()
    ]})


app.add_middleware(BoundedBody)
app.add_middleware(PublicCompression)
app.middleware("http")(safeguards)
for module in (auth, profile, library, symptoms, history, images, knowledge, admin, icd):
    app.include_router(module.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


# Serve the production React build from the same origin as the API.
FRONTEND = Path(
    os.getenv("FRONTEND_DIST", str(PROJECT_ROOT / "frontend" / "dist"))
)
if (FRONTEND / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")


@app.get("/")
def index():
    if not (FRONTEND / "index.html").exists():
        raise HTTPException(503, "Frontend chưa build. Chạy npm run build trong thư mục frontend.")
    return FileResponse(FRONTEND / "index.html")
