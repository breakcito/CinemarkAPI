import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.database import init_db
from .routes.telemetry import router as telemetry_router
from .routes.survey import router as survey_router
from .routes.analytics import router as analytics_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cinemark_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando API de Cinemark Usabilidad & Telemetría...")
    try:
        init_db()
        logger.info("Base de datos conectada e inicializada correctamente.")
    except Exception as e:
        logger.error(f"Advertencia al conectar DB en startup: {e}")
    yield
    logger.info("Apagando API de Cinemark...")

app = FastAPI(
    title="Cinemark Usability Telemetry & Research API",
    description="Backend para recolección de métricas de usabilidad (eficiencia, eficacia, satisfacción SUS) para la tesis de rediseño UX/IHC de Cinemark.",
    version="1.0.0",
    lifespan=lifespan
)

# Configuración de CORS permisiva para prototipo móvil, emuladores y pruebas locales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas con prefijo de API v1
app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(survey_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "Cinemark Usability Telemetry API",
        "version": "1.0.0",
        "docs": "/docs"
    }
