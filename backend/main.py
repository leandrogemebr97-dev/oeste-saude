from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes import router

FRONTEND = Path(__file__).parent / "frontend"

app = FastAPI(
    title="Rol ANS — Oeste Saúde",
    description="Consulta de procedimentos cobertos e diretrizes de utilização (DUT).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(FRONTEND / "pages" / "index.html")

app.mount("/", StaticFiles(directory=FRONTEND), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
