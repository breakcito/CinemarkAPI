from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from ..models.schemas import (
    SessionStartRequest,
    StepDurationEvent,
    ErrorEvent,
    SessionCompleteRequest,
    SessionFullSyncRequest,
    ParticipantCreateRequest,
    PretestObservationRequest,
    ParticipantActivateRequest,
)
from ..services.telemetry_service import TelemetryService
from ..core.ws_manager import ws_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["Telemetría de Usabilidad"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Canal de comunicación en tiempo real para sincronizar participantes
    y evaluaciones entre múltiples dispositivos sin necesidad de sondeo (polling).
    """
    await ws_manager.connect(websocket)
    try:
        active = TelemetryService.get_active_participant()
        await websocket.send_json({
            "event": "initial_state",
            "active_participant": active.get("participant")
        })
        while True:
            # Mantener la conexión abierta escuchando mensajes o pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"Excepción en WebSocket: {e}")
        ws_manager.disconnect(websocket)

@router.post("/session/start", status_code=status.HTTP_201_CREATED)
async def start_session(req: SessionStartRequest):
    try:
        result = TelemetryService.start_session(req)
        await ws_manager.broadcast({
            "event": "session_started",
            "session_uuid": req.session_uuid,
            "participant_code": req.participant_code
        })
        return result
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
async def complete_session(req: SessionCompleteRequest):
    try:
        result = TelemetryService.complete_session(req)
        await ws_manager.broadcast({
            "event": "session_completed",
            "session_uuid": req.session_uuid,
            "participant_code": req.participant_code
        })
        return result
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

@router.post("/participant", status_code=status.HTTP_201_CREATED)
async def register_participant(req: ParticipantCreateRequest):
    try:
        result = TelemetryService.register_participant(req)
        active = TelemetryService.get_active_participant()
        await ws_manager.broadcast({
            "event": "participant_activated",
            "participant": active.get("participant")
        })
        return result
    except Exception as e:
        logger.error(f"Error al registrar participante: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/participant/activate", status_code=status.HTTP_200_OK)
async def activate_participant(req: ParticipantActivateRequest):
    try:
        result = TelemetryService.activate_participant(req.participant_code)
        active = TelemetryService.get_active_participant()
        await ws_manager.broadcast({
            "event": "participant_activated",
            "participant": active.get("participant")
        })
        return result
    except Exception as e:
        logger.error(f"Error al activar participante: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/participant/clear", status_code=status.HTTP_200_OK)
async def clear_active_participant():
    try:
        result = TelemetryService.clear_active_participant()
        await ws_manager.broadcast({
            "event": "participant_cleared"
        })
        return result
    except Exception as e:
        logger.error(f"Error al limpiar participante activo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/participant/active")
def get_active_participant():
    try:
        return TelemetryService.get_active_participant()
    except Exception as e:
        logger.error(f"Error al consultar participante activo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/participants")
def get_participants():
    try:
        return TelemetryService.get_participants()
    except Exception as e:
        logger.error(f"Error al listar participantes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pretest-observation", status_code=status.HTTP_201_CREATED)
async def record_pretest_observation(req: PretestObservationRequest):
    try:
        result = TelemetryService.record_pretest_observation(req)
        await ws_manager.broadcast({
            "event": "observation_saved",
            "participant_code": req.participant_code,
            "test_mode": req.test_mode
        })
        return result
    except Exception as e:
        logger.error(f"Error al registrar observación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/observation/{participant_code}")
def get_observation_sheet(participant_code: str, test_mode: str = "pretest"):
    try:
        return TelemetryService.get_observation_sheet(participant_code, test_mode)
    except Exception as e:
        logger.error(f"Error al obtener ficha de observación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
def get_telemetry_health():
    try:
        return TelemetryService.check_database_health()
    except Exception as e:
        logger.error(f"Error al verificar estado de la base de datos: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

