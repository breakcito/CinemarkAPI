from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
from ..models.schemas import AnalyticsSummaryResponse
from ..services.analytics_service import AnalyticsService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Métricas de Resultados de Tesis"])

@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_summary(test_mode: Optional[str] = Query(None, description="Filtrar por 'pretest' o 'posttest'")):
    try:
        return AnalyticsService.get_summary(test_mode=test_mode)
    except Exception as e:
        logger.error(f"Error al obtener métricas de resultados: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/sessions.csv")
def export_sessions_csv(test_mode: Optional[str] = Query(None)):
    try:
        csv_content = AnalyticsService.export_sessions_csv(test_mode=test_mode)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=telemetry_sessions.csv"}
        )
    except Exception as e:
        logger.error(f"Error al exportar sesiones CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/sus.csv")
def export_sus_csv(test_mode: Optional[str] = Query(None)):
    try:
        csv_content = AnalyticsService.export_sus_csv(test_mode=test_mode)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sus_responses.csv"}
        )
    except Exception as e:
        logger.error(f"Error al exportar SUS CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/steps.csv")
def export_steps_csv(test_mode: Optional[str] = Query(None)):
    try:
        csv_content = AnalyticsService.export_step_durations_csv(test_mode=test_mode)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=step_durations.csv"}
        )
    except Exception as e:
        logger.error(f"Error al exportar etapas CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))
