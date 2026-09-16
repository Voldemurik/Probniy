from pathlib import Path
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routers import scan, report

# === ПУТЬ К ФРОНТЕНДУ ===
BASE_DIR = Path(__file__).resolve().parents[2]
WEB_DIR = BASE_DIR / "web" / "design" / "website final" / "public"
_INDEX_HTML = WEB_DIR / "app.html"

app = FastAPI(
    title="Подписки-сканер",
    version="1.7.0",
    description="Поиск регулярных подписок в банковской выписке",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan.router)
app.include_router(report.router)


@app.get("/", include_in_schema=False)
def root():
    if _INDEX_HTML.exists():
        return FileResponse(_INDEX_HTML)
    return JSONResponse({
        "message": "Подписки-сканер API",
        "docs": "/docs",
        "note": f"index.html не найден в {WEB_DIR}",
    })


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)