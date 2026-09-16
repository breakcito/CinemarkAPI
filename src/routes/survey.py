from fastapi import APIRouter, HTTPException, status
from ..models.schemas import SusSurveyRequest, SusSurveyResponse
from ..services.telemetry_service import TelemetryService
from ..core.database import get_db_cursor
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
