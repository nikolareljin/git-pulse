"""GitPulse Main Application"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging

from app.api.routes import router as api_router
from app.models.database import init_db
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting GitPulse...")
    await init_db()
    logger.info(f"Repositories directory: {config.REPOSITORIES_DIR}")
    logger.info(f"Ollama host: {config.OLLAMA_HOST}")
    yield
    logger.info("Shutting down GitPulse...")


app = FastAPI(
    title="GitPulse",
    description="AI-powered Git repository contributor analysis",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG
    )
