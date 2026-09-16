import logging
from datetime import datetime
from typing import Dict, Any
from ..core.database import get_db_cursor
from ..models.schemas import (
    SessionStartRequest,
    StepDurationEvent,
    ErrorEvent,
    SessionCompleteRequest,
    SessionFullSyncRequest,
    SusSurveyRequest,
    SusSurveyResponse,
)

logger = logging.getLogger(__name__)

class TelemetryService:
    @staticmethod
    def start_session(req: SessionStartRequest) -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("""
            INSERT INTO telemetry_sessions (
                session_uuid, participant_code, test_mode,
                cinema_id, cinema_name, movie_id, movie_title,
                started_at, device_info, is_completed, max_step_reached
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                participant_code = VALUES(participant_code),
                test_mode = VALUES(test_mode),
                cinema_id = VALUES(cinema_id),
                cinema_name = VALUES(cinema_name),
                movie_id = VALUES(movie_id),
                movie_title = VALUES(movie_title),
                device_info = VALUES(device_info)
            """, (
                req.session_uuid,
                req.participant_code or "ANONIMO",
                req.test_mode or "posttest",
                req.cinema_id,
                req.cinema_name,
                req.movie_id,
                req.movie_title,
                req.started_at or datetime.now(),
                req.device_info,
                False,
                "Splash"
            ))
            logger.info(f"Sesión iniciada: {req.session_uuid} (Participante: {req.participant_code})")
            return {"status": "ok", "session_uuid": req.session_uuid}

    @staticmethod
    def record_step(step: StepDurationEvent) -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("""
            INSERT INTO telemetry_step_durations (
                session_uuid, step_name, duration_seconds, started_at, ended_at
            ) VALUES (%s, %s, %s, %s, %s)
            """, (
                step.session_uuid,
                step.step_name,
                step.duration_seconds,
                step.started_at,
                step.ended_at or datetime.now()
            ))

            # Actualizar max_step_reached en la sesión si existe
            cursor.execute("""
            UPDATE telemetry_sessions
            SET max_step_reached = %s
            WHERE session_uuid = %s
            """, (step.step_name, step.session_uuid))

            return {"status": "ok", "step_name": step.step_name, "duration": step.duration_seconds}

    @staticmethod
    def record_error(err: ErrorEvent) -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("""
            INSERT INTO telemetry_errors (
                session_uuid, step_name, error_type, description, occurred_at
            ) VALUES (%s, %s, %s, %s, %s)
            """, (
                err.session_uuid,
                err.step_name,
                err.error_type,
                err.description,
                err.occurred_at or datetime.now()
            ))

            cursor.execute("""
            UPDATE telemetry_sessions
            SET total_errors = total_errors + 1
            WHERE session_uuid = %s
            """, (err.session_uuid,))

            return {"status": "ok", "error_type": err.error_type}

    @staticmethod
    def complete_session(req: SessionCompleteRequest) -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("""
            UPDATE telemetry_sessions
            SET is_completed = %s,
                max_step_reached = %s,
                total_duration_seconds = %s,
                ended_at = %s
            WHERE session_uuid = %s
            """, (
                req.is_completed,
                req.max_step_reached,
                req.total_duration_seconds,
                req.ended_at or datetime.now(),
                req.session_uuid
            ))
            return {"status": "ok", "session_uuid": req.session_uuid, "is_completed": req.is_completed}

    @staticmethod
    def sync_full_session(req: SessionFullSyncRequest) -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("""
            INSERT INTO telemetry_sessions (
                session_uuid, participant_code, test_mode,
                cinema_id, cinema_name, movie_id, movie_title,
                started_at, ended_at, total_duration_seconds,
                is_completed, max_step_reached, total_errors, device_info
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                participant_code = VALUES(participant_code),
                test_mode = VALUES(test_mode),
                cinema_id = VALUES(cinema_id),
                cinema_name = VALUES(cinema_name),
                movie_id = VALUES(movie_id),
                movie_title = VALUES(movie_title),
                ended_at = VALUES(ended_at),
                total_duration_seconds = VALUES(total_duration_seconds),
                is_completed = VALUES(is_completed),
                max_step_reached = VALUES(max_step_reached),
                total_errors = VALUES(total_errors),
                device_info = VALUES(device_info)
            """, (
                req.session_uuid,
                req.participant_code or "ANONIMO",
                req.test_mode or "posttest",
                req.cinema_id,
                req.cinema_name,
                req.movie_id,
                req.movie_title,
                req.started_at,
                req.ended_at or datetime.now(),
                req.total_duration_seconds,
                req.is_completed,
                req.max_step_reached,
                len(req.errors),
                req.device_info
            ))

            for step in req.steps:
                cursor.execute("""
                INSERT INTO telemetry_step_durations (
                    session_uuid, step_name, duration_seconds, started_at, ended_at
                ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    req.session_uuid,
                    step.get("step_name", "Desconocido"),
                    float(step.get("duration_seconds", 0.0)),
                    step.get("started_at"),
                    step.get("ended_at")
                ))

            for err in req.errors:
                cursor.execute("""
                INSERT INTO telemetry_errors (
                    session_uuid, step_name, error_type, description, occurred_at
                ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    req.session_uuid,
                    err.get("step_name", "General"),
                    err.get("error_type", "General"),
                    err.get("description", ""),
                    err.get("occurred_at") or datetime.now()
                ))

            return {"status": "ok", "message": "Sesión completa sincronizada con éxito"}

    @staticmethod
    def calculate_sus_score(q1: int, q2: int, q3: int, q4: int, q5: int,
                            q6: int, q7: int, q8: int, q9: int, q10: int) -> tuple[float, str]:
        # Ítems impares (1, 3, 5, 7, 9): puntaje = respuesta - 1
        positives = (q1 - 1) + (q3 - 1) + (q5 - 1) + (q7 - 1) + (q9 - 1)
        # Ítems pares (2, 4, 6, 8, 10): puntaje = 5 - respuesta
        negatives = (5 - q2) + (5 - q4) + (5 - q6) + (5 - q8) + (5 - q10)
        # Total multiplicado por 2.5 para escalar a 0-100
        raw_score = (positives + negatives) * 2.5
        sus_score = round(raw_score, 2)

        # Calificación adjetival según Bangor, Kortum & Miller (2009)
        if sus_score >= 85.0:
            adjective = "Excelente (Grade A)"
        elif sus_score >= 70.0:
            adjective = "Bueno (Grade B)"
        elif sus_score >= 50.0:
            adjective = "Aceptable / Regular (Grade C)"
        elif sus_score >= 35.0:
            adjective = "Pobre (Grade D)"
        else:
            adjective = "Inaceptable (Grade F)"

        return sus_score, adjective

    @staticmethod
    def submit_sus_survey(req: SusSurveyRequest) -> SusSurveyResponse:
        score, adjective = TelemetryService.calculate_sus_score(
            req.q1, req.q2, req.q3, req.q4, req.q5,
            req.q6, req.q7, req.q8, req.q9, req.q10
        )

        with get_db_cursor() as cursor:
            cursor.execute("""
            INSERT INTO sus_survey_responses (
                session_uuid, participant_code, test_mode,
                q1, q2, q3, q4, q5, q6, q7, q8, q9, q10,
                sus_score, adjective_rating, comments
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                req.session_uuid,
                req.participant_code,
                req.test_mode,
                req.q1, req.q2, req.q3, req.q4, req.q5,
                req.q6, req.q7, req.q8, req.q9, req.q10,
                score, adjective, req.comments
            ))
            inserted_id = cursor.lastrowid

            return SusSurveyResponse(
                id=inserted_id,
                participant_code=req.participant_code,
                test_mode=req.test_mode,
                sus_score=score,
                adjective_rating=adjective,
                submitted_at=datetime.now()
            )
