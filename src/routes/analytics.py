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

@router.get("/wilcoxon-matrix")
def get_wilcoxon_matrix():
    try:
        return AnalyticsService.get_wilcoxon_matrix()
    except Exception as e:
        logger.error(f"Error al generar matriz de Wilcoxon: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/thesis-dataset.csv")
def export_thesis_dataset_csv():
    try:
        csv_content = AnalyticsService.export_wilcoxon_csv()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cinemark_tesis_dataset_wilcoxon.csv"}
        )
    except Exception as e:
        logger.error(f"Error al exportar dataset pareado de tesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report-html", response_class=Response)
def get_report_html():
    """
    Entrega el reporte formal académico de resultados de tesis (APA 7, fondo blanco puro #FFFFFF)
    directamente en el navegador sin depender de scripts externos.
    """
    try:
        from ..services.thesis_report_service import ThesisReportService
        html_content = ThesisReportService.generate_html_report()
        return Response(content=html_content, media_type="text/html")
    except Exception as e:
        logger.error(f"Error al generar reporte HTML in-process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report-zip")
def get_report_zip():
    """
    Descarga un paquete ZIP autónomo que contiene el reporte HTML APA 7,
    las 5 figuras estadísticas en alta resolución (PNG a 300 DPI con fondo blanco)
    y el dataset pareado en formato CSV listo para SPSS / Excel.
    """
    try:
        from ..services.thesis_report_service import ThesisReportService
        zip_bytes = ThesisReportService.generate_zip_package()
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=cinemark_reporte_tesis_apa7.zip"}
        )
    except Exception as e:
        logger.error(f"Error al generar paquete ZIP de tesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

