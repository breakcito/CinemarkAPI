from fastapi import APIRouter, HTTPException, status
from ..models.schemas import (
    SusSurveyRequest,
    SusSurveyResponse,
    ComparativeSurveyRequest,
    ComparativeSurveyResponse,
)
from ..services.telemetry_service import TelemetryService
from ..core.database import get_db_cursor
from ..core.ws_manager import ws_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/survey", tags=["Escala de Usabilidad del Sistema (SUS)"])

@router.post("/sus", response_model=SusSurveyResponse, status_code=status.HTTP_201_CREATED)
def submit_sus_survey(req: SusSurveyRequest):
    try:
        return TelemetryService.submit_sus_survey(req)
    except Exception as e:
        logger.error(f"Error al guardar encuesta SUS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sus")
def list_sus_surveys(limit: int = 50):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
            SELECT id, participant_code, test_mode, sus_score, adjective_rating, comments, submitted_at
            FROM sus_survey_responses
            ORDER BY submitted_at DESC
            LIMIT %s
            """, (limit,))
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error al listar encuestas SUS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comparative", response_model=ComparativeSurveyResponse, status_code=status.HTTP_201_CREATED)
async def submit_comparative_survey(req: ComparativeSurveyRequest):
    """
    Registra la evaluación simultánea comparativa Pretest (App Oficial) vs Posttest (Prototipo),
    calculando ambos puntajes SUS y guardando la matriz para la tesis.
    """
    try:
        result = TelemetryService.submit_comparative_survey(req)
        await ws_manager.broadcast({
            "event": "survey_saved",
            "participant_code": req.participant_code
        })
        return result
    except Exception as e:
        logger.error(f"Error al registrar encuesta comparativa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/comparative/{participant_code}")
def get_comparative_survey(participant_code: str):
    try:
        data = TelemetryService.get_comparative_survey(participant_code)
        if not data:
            raise HTTPException(status_code=404, detail="No se encontró evaluación comparativa para este participante")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener encuesta comparativa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/comparative")
def list_comparative_surveys(limit: int = 50):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
            SELECT * FROM comparative_surveys
            ORDER BY submitted_at DESC
            LIMIT %s
            """, (limit,))
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error al listar encuestas comparativas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
