from fastapi import APIRouter, HTTPException, status
from ..models.schemas import (
    SessionStartRequest,
    StepDurationEvent,
    ErrorEvent,
    SessionCompleteRequest,
    SessionFullSyncRequest,
)
from ..services.telemetry_service import TelemetryService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["Telemetría de Usabilidad"])

@router.post("/session/start", status_code=status.HTTP_201_CREATED)
def start_session(req: SessionStartRequest):
    try:
        return TelemetryService.start_session(req)
    except Exception as e:
        logger.error(f"Error al iniciar sesión de telemetría: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/step", status_code=status.HTTP_200_OK)
def record_step(step: StepDurationEvent):
    try:
        return TelemetryService.record_step(step)
    except Exception as e:
        logger.error(f"Error al registrar paso: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/error", status_code=status.HTTP_200_OK)
def record_error(err: ErrorEvent):
    try:
        return TelemetryService.record_error(err)
    except Exception as e:
        logger.error(f"Error al registrar incidencia: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/complete", status_code=status.HTTP_200_OK)
def complete_session(req: SessionCompleteRequest):
    try:
        return TelemetryService.complete_session(req)
    except Exception as e:
        logger.error(f"Error al finalizar sesión: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/sync", status_code=status.HTTP_200_OK)
def sync_full_session(req: SessionFullSyncRequest):
    try:
        return TelemetryService.sync_full_session(req)
    except Exception as e:
        logger.error(f"Error al sincronizar sesión completa: {e}")
        raise HTTPException(status_code=500, detail=str(e))
