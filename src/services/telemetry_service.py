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
    ComparativeSurveyRequest,
    ComparativeSurveyResponse,
    ParticipantCreateRequest,
    ParticipantResponse,
    PretestObservationRequest,
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
                session_uuid, step_name, duration_seconds, taps_count, started_at, ended_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                step.session_uuid,
                step.step_name,
                step.duration_seconds,
                step.taps_count or 0,
                step.started_at,
                step.ended_at or datetime.now()
            ))

            # Actualizar max_step_reached y taps en la sesión si existe
            cursor.execute("""
            UPDATE telemetry_sessions
            SET max_step_reached = %s,
                taps_count = taps_count + %s
            WHERE session_uuid = %s
            """, (step.step_name, step.taps_count or 0, step.session_uuid))

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
                taps_count = CASE WHEN %s > 0 THEN %s ELSE taps_count END,
                participant_code = CASE WHEN %s IS NOT NULL AND %s != 'ANONIMO' THEN %s ELSE participant_code END,
                total_errors = CASE WHEN %s IS NOT NULL THEN %s ELSE total_errors END,
                ended_at = %s
            WHERE session_uuid = %s
            """, (
                req.is_completed,
                req.max_step_reached,
                req.total_duration_seconds,
                req.taps_count or 0,
                req.taps_count or 0,
                req.participant_code,
                req.participant_code,
                req.participant_code,
                req.total_errors,
                req.total_errors,
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

    @staticmethod
    def submit_comparative_survey(req: ComparativeSurveyRequest) -> ComparativeSurveyResponse:
        pre_q_vals = [
            req.pre_q1, req.pre_q2, req.pre_q3, req.pre_q4, req.pre_q5,
            req.pre_q6, req.pre_q7, req.pre_q8, req.pre_q9, req.pre_q10
        ]
        post_q_vals = [
            req.post_q1, req.post_q2, req.post_q3, req.post_q4, req.post_q5,
            req.post_q6, req.post_q7, req.post_q8, req.post_q9, req.post_q10
        ]

        pre_score, pre_adj = TelemetryService.calculate_sus_score(*pre_q_vals)
        post_score, post_adj = TelemetryService.calculate_sus_score(*post_q_vals)
        diff_score = round(post_score - pre_score, 2)
        base = pre_score if pre_score > 0 else 1.0
        pct_imp = round(((post_score - pre_score) / base) * 100.0, 2)

        with get_db_cursor() as cursor:
            # 1. Asegurar participante
            cursor.execute("""
            INSERT IGNORE INTO participants (participant_code, name, test_mode)
            VALUES (%s, %s, 'posttest')
            """, (req.participant_code, f"Participante {req.participant_code}"))

            # 2. Guardar o actualizar respuestas Pre-test en sus_survey_responses
            cursor.execute("""
            SELECT id FROM sus_survey_responses
            WHERE participant_code = %s AND test_mode = 'pretest'
            ORDER BY submitted_at DESC LIMIT 1
            """, (req.participant_code,))
            existing_pre = cursor.fetchone()

            if existing_pre:
                cursor.execute("""
                UPDATE sus_survey_responses
                SET q1=%s, q2=%s, q3=%s, q4=%s, q5=%s, q6=%s, q7=%s, q8=%s, q9=%s, q10=%s,
                    sus_score=%s, adjective_rating=%s, comments=%s
                WHERE id = %s
                """, (*pre_q_vals, pre_score, pre_adj, req.comments, existing_pre["id"]))
            else:
                cursor.execute("""
                INSERT INTO sus_survey_responses (
                    participant_code, test_mode,
                    q1, q2, q3, q4, q5, q6, q7, q8, q9, q10,
                    sus_score, adjective_rating, comments
                ) VALUES (%s, 'pretest', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (req.participant_code, *pre_q_vals, pre_score, pre_adj, req.comments))

            # 3. Guardar o actualizar respuestas Post-test en sus_survey_responses
            cursor.execute("""
            SELECT id FROM sus_survey_responses
            WHERE participant_code = %s AND test_mode = 'posttest'
            ORDER BY submitted_at DESC LIMIT 1
            """, (req.participant_code,))
            existing_post = cursor.fetchone()

            if existing_post:
                cursor.execute("""
                UPDATE sus_survey_responses
                SET q1=%s, q2=%s, q3=%s, q4=%s, q5=%s, q6=%s, q7=%s, q8=%s, q9=%s, q10=%s,
                    sus_score=%s, adjective_rating=%s, comments=%s
                WHERE id = %s
                """, (*post_q_vals, post_score, post_adj, req.comments, existing_post["id"]))
            else:
                cursor.execute("""
                INSERT INTO sus_survey_responses (
                    participant_code, test_mode,
                    q1, q2, q3, q4, q5, q6, q7, q8, q9, q10,
                    sus_score, adjective_rating, comments
                ) VALUES (%s, 'posttest', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (req.participant_code, *post_q_vals, post_score, post_adj, req.comments))

            # 4. Guardar o actualizar en comparative_surveys
            cursor.execute("""
            INSERT INTO comparative_surveys (
                participant_code,
                pre_q1, pre_q2, pre_q3, pre_q4, pre_q5, pre_q6, pre_q7, pre_q8, pre_q9, pre_q10,
                post_q1, post_q2, post_q3, post_q4, post_q5, post_q6, post_q7, post_q8, post_q9, post_q10,
                pre_sus_score, post_sus_score, diff_sus_score,
                pre_adjective, post_adjective,
                heuristic_error_pre, heuristic_error_post,
                heuristic_seats_pre, heuristic_seats_post,
                heuristic_timer_pre, heuristic_timer_post,
                preferred_system, comments
            ) VALUES (
                %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            ) ON DUPLICATE KEY UPDATE
                pre_q1 = VALUES(pre_q1), pre_q2 = VALUES(pre_q2), pre_q3 = VALUES(pre_q3),
                pre_q4 = VALUES(pre_q4), pre_q5 = VALUES(pre_q5), pre_q6 = VALUES(pre_q6),
                pre_q7 = VALUES(pre_q7), pre_q8 = VALUES(pre_q8), pre_q9 = VALUES(pre_q9),
                pre_q10 = VALUES(pre_q10),
                post_q1 = VALUES(post_q1), post_q2 = VALUES(post_q2), post_q3 = VALUES(post_q3),
                post_q4 = VALUES(post_q4), post_q5 = VALUES(post_q5), post_q6 = VALUES(post_q6),
                post_q7 = VALUES(post_q7), post_q8 = VALUES(post_q8), post_q9 = VALUES(post_q9),
                post_q10 = VALUES(post_q10),
                pre_sus_score = VALUES(pre_sus_score), post_sus_score = VALUES(post_sus_score),
                diff_sus_score = VALUES(diff_sus_score),
                pre_adjective = VALUES(pre_adjective), post_adjective = VALUES(post_adjective),
                heuristic_error_pre = VALUES(heuristic_error_pre), heuristic_error_post = VALUES(heuristic_error_post),
                heuristic_seats_pre = VALUES(heuristic_seats_pre), heuristic_seats_post = VALUES(heuristic_seats_post),
                heuristic_timer_pre = VALUES(heuristic_timer_pre), heuristic_timer_post = VALUES(heuristic_timer_post),
                preferred_system = VALUES(preferred_system), comments = VALUES(comments),
                submitted_at = CURRENT_TIMESTAMP
            """, (
                req.participant_code,
                *pre_q_vals,
                *post_q_vals,
                pre_score, post_score, diff_score,
                pre_adj, post_adj,
                req.heuristic_error_pre or 3, req.heuristic_error_post or 5,
                req.heuristic_seats_pre or 3, req.heuristic_seats_post or 5,
                req.heuristic_timer_pre or 2, req.heuristic_timer_post or 5,
                req.preferred_system or "Prototipo",
                req.comments
            ))

        logger.info(f"Cuestionario comparativo guardado para {req.participant_code}: Pre={pre_score} pts, Post={post_score} pts (Δ={diff_score})")

        return ComparativeSurveyResponse(
            participant_code=req.participant_code,
            pre_sus_score=pre_score,
            post_sus_score=post_score,
            diff_sus_score=diff_score,
            pct_improvement=pct_imp,
            pre_adjective=pre_adj,
            post_adjective=post_adj,
            submitted_at=datetime.now(),
            message="Evaluación comparativa guardada exitosamente"
        )

    @staticmethod
    def get_comparative_survey(participant_code: str) -> Dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute("""
            SELECT * FROM comparative_surveys
            WHERE participant_code = %s
            LIMIT 1
            """, (participant_code,))
            return cursor.fetchone()

    @staticmethod
    def register_participant(req: ParticipantCreateRequest) -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("""
            INSERT INTO participants (
                participant_code, name, age, gender, cinema_frequency, notes, is_active, last_active_at
            ) VALUES (%s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                age = VALUES(age),
                gender = VALUES(gender),
                cinema_frequency = VALUES(cinema_frequency),
                notes = VALUES(notes),
                is_active = TRUE,
                last_active_at = CURRENT_TIMESTAMP
            """, (
                req.participant_code,
                req.name,
                req.age,
                req.gender,
                req.cinema_frequency,
                req.notes
            ))
            # Desactivar a los demás para que quede un único participante activo de forma limpia
            cursor.execute("""
            UPDATE participants 
            SET is_active = FALSE 
            WHERE participant_code != %s
            """, (req.participant_code,))
            logger.info(f"Participante registrado y activado: {req.participant_code}")
            return {"status": "ok", "participant_code": req.participant_code}

    @staticmethod
    def activate_participant(participant_code: str) -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE participants SET is_active = FALSE")
            cursor.execute("""
            UPDATE participants 
            SET is_active = TRUE, last_active_at = CURRENT_TIMESTAMP 
            WHERE participant_code = %s
            """, (participant_code,))
            logger.info(f"Participante activado para sincronización en tiempo real: {participant_code}")
            return {"status": "ok", "active_participant": participant_code}

    @staticmethod
    def clear_active_participant() -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE participants SET is_active = FALSE")
            logger.info("Participante activo desactivado en base de datos")
            return {"status": "ok", "active": False}

    @staticmethod
    def get_active_participant() -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("""
            SELECT id, participant_code, name, age, gender, cinema_frequency, notes, is_active, last_active_at
            FROM participants
            WHERE is_active = TRUE
            ORDER BY last_active_at DESC
            LIMIT 1
            """)
            active = cursor.fetchone()
            if not active:
                return {"active": False, "participant": None}
            return {"active": True, "participant": active}

    @staticmethod
    def get_participants() -> list[Dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute("""
            SELECT 
                p.id, 
                p.participant_code, 
                p.name, 
                p.age, 
                p.gender, 
                p.cinema_frequency, 
                p.notes, 
                p.is_active,
                p.last_active_at,
                p.created_at,
                (SELECT COUNT(*) FROM telemetry_sessions s WHERE s.participant_code = p.participant_code AND s.test_mode = 'pretest') > 0 as has_pretest,
                (SELECT COUNT(*) FROM telemetry_sessions s WHERE s.participant_code = p.participant_code AND s.test_mode = 'posttest') > 0 as has_posttest,
                (SELECT COUNT(*) FROM comparative_surveys c WHERE c.participant_code = p.participant_code) > 0 as has_comparative,
                (SELECT total_duration_seconds FROM telemetry_sessions s WHERE s.participant_code = p.participant_code AND s.test_mode = 'pretest' ORDER BY id DESC LIMIT 1) as pretest_time_s,
                (SELECT total_duration_seconds FROM telemetry_sessions s WHERE s.participant_code = p.participant_code AND s.test_mode = 'posttest' ORDER BY id DESC LIMIT 1) as posttest_time_s,
                (SELECT total_errors FROM telemetry_sessions s WHERE s.participant_code = p.participant_code AND s.test_mode = 'pretest' ORDER BY id DESC LIMIT 1) as pretest_errors,
                (SELECT total_errors FROM telemetry_sessions s WHERE s.participant_code = p.participant_code AND s.test_mode = 'posttest' ORDER BY id DESC LIMIT 1) as posttest_errors,
                (SELECT is_completed FROM telemetry_sessions s WHERE s.participant_code = p.participant_code AND s.test_mode = 'pretest' ORDER BY id DESC LIMIT 1) as pretest_completed,
                (SELECT is_completed FROM telemetry_sessions s WHERE s.participant_code = p.participant_code AND s.test_mode = 'posttest' ORDER BY id DESC LIMIT 1) as posttest_completed,
                (SELECT pre_sus_score FROM comparative_surveys c WHERE c.participant_code = p.participant_code ORDER BY id DESC LIMIT 1) as pre_sus_score,
                (SELECT post_sus_score FROM comparative_surveys c WHERE c.participant_code = p.participant_code ORDER BY id DESC LIMIT 1) as post_sus_score,
                (SELECT diff_sus_score FROM comparative_surveys c WHERE c.participant_code = p.participant_code ORDER BY id DESC LIMIT 1) as diff_sus_score
            FROM participants p
            ORDER BY p.id ASC
            """)
            rows = cursor.fetchall()
            for r in rows:
                r["has_pretest"] = bool(r.get("has_pretest"))
                r["has_posttest"] = bool(r.get("has_posttest"))
                r["has_comparative"] = bool(r.get("has_comparative"))
                r["is_active"] = bool(r.get("is_active"))
                if r.get("pretest_completed") is not None:
                    r["pretest_completed"] = bool(r["pretest_completed"])
                if r.get("posttest_completed") is not None:
                    r["posttest_completed"] = bool(r["posttest_completed"])
                if r.get("pre_sus_score") is not None:
                    r["pre_sus_score"] = float(r["pre_sus_score"])
                if r.get("post_sus_score") is not None:
                    r["post_sus_score"] = float(r["post_sus_score"])
                if r.get("diff_sus_score") is not None:
                    r["diff_sus_score"] = float(r["diff_sus_score"])
            return rows

    @staticmethod
    def get_observation_sheet(participant_code: str, test_mode: str = "pretest") -> Dict[str, Any]:
        """
        Recupera la ficha de observación guardada previamente (Pretest o Posttest)
        para mostrar inmediatamente los datos al investigador sin pantallas vacías.
        """
        with get_db_cursor() as cursor:
            cursor.execute("""
            SELECT session_uuid, participant_code, test_mode, total_duration_seconds,
                   is_completed, max_step_reached, total_errors, taps_count, notes, device_info, created_at
            FROM telemetry_sessions
            WHERE participant_code = %s AND test_mode = %s
            ORDER BY id DESC
            LIMIT 1
            """, (participant_code, test_mode))
            session = cursor.fetchone()

            if not session:
                return {
                    "found": False,
                    "participant_code": participant_code,
                    "test_mode": test_mode,
                    "session_uuid": None,
                    "is_completed": True,
                    "max_step_reached": "Historial",
                    "total_duration_seconds": 0.0,
                    "total_errors": 0,
                    "taps_count": 0,
                    "step_durations": {},
                    "errors": [],
                    "notes": "",
                    "created_at": None
                }

            session_uuid = session["session_uuid"]

            # Obtener duraciones por etapa
            cursor.execute("""
            SELECT step_name, duration_seconds
            FROM telemetry_step_durations
            WHERE session_uuid = %s
            ORDER BY id ASC
            """, (session_uuid,))
            step_rows = cursor.fetchall()
            step_durations = {row["step_name"]: float(row["duration_seconds"]) for row in step_rows}

            # Obtener incidencias y errores observados
            cursor.execute("""
            SELECT step_name, error_type, description
            FROM telemetry_errors
            WHERE session_uuid = %s
            ORDER BY id ASC
            """, (session_uuid,))
            error_rows = cursor.fetchall()
            errors_list = [
                {
                    "step_name": err["step_name"],
                    "error_type": err["error_type"],
                    "description": err.get("description") or ""
                }
                for err in error_rows
            ]

            note_text = session.get("notes") or ""
            if not note_text and session.get("device_info"):
                info = session.get("device_info") or ""
                if " - " in info:
                    note_text = info.split(" - ", 1)[1]

            return {
                "found": True,
                "participant_code": participant_code,
                "test_mode": test_mode,
                "session_uuid": session_uuid,
                "is_completed": bool(session.get("is_completed")),
                "max_step_reached": session.get("max_step_reached") or "Historial",
                "total_duration_seconds": float(session.get("total_duration_seconds") or 0.0),
                "total_errors": int(session.get("total_errors") or len(errors_list)),
                "taps_count": int(session.get("taps_count") or 0),
                "step_durations": step_durations,
                "errors": errors_list,
                "notes": note_text,
                "created_at": session.get("created_at")
            }

    @staticmethod
    def record_pretest_observation(req: PretestObservationRequest) -> Dict[str, Any]:
        """
        Registra o actualiza la Ficha de Observación (Pretest o Posttest).
        Si ya existe una sesión previa para (participant_code, test_mode),
        actualiza la sesión existente de forma limpia evitando registros duplicados.
        """
        test_mode = req.test_mode or "pretest"
        started_at = datetime.now()

        with get_db_cursor() as cursor:
            # 1. Asegurar registro del participante
            cursor.execute("""
            INSERT IGNORE INTO participants (participant_code, name, test_mode)
            VALUES (%s, %s, %s)
            """, (req.participant_code, f"Participante {req.participant_code}", test_mode))

            # 2. Verificar si ya existe sesión para actualizar o insertar
            cursor.execute("""
            SELECT session_uuid FROM telemetry_sessions
            WHERE participant_code = %s AND test_mode = %s
            ORDER BY id DESC LIMIT 1
            """, (req.participant_code, test_mode))
            existing = cursor.fetchone()

            if existing:
                session_uuid = existing["session_uuid"]
                cursor.execute("""
                UPDATE telemetry_sessions
                SET cinema_name = %s,
                    movie_title = %s,
                    ended_at = %s,
                    total_duration_seconds = %s,
                    is_completed = %s,
                    max_step_reached = %s,
                    total_errors = %s,
                    taps_count = %s,
                    notes = %s,
                    device_info = %s
                WHERE session_uuid = %s
                """, (
                    req.cinema_name or "Cinemark Mallplaza Trujillo (App Oficial)",
                    req.movie_title or "Evaluación App Oficial",
                    started_at,
                    req.total_duration_seconds,
                    req.is_completed,
                    req.max_step_reached,
                    req.total_errors,
                    req.taps_count or 0,
                    req.notes or "",
                    f"Ficha de Observación ({test_mode}) - {req.notes or ''}",
                    session_uuid
                ))
                # Reemplazar duraciones por etapa y errores
                cursor.execute("DELETE FROM telemetry_step_durations WHERE session_uuid = %s", (session_uuid,))
                cursor.execute("DELETE FROM telemetry_errors WHERE session_uuid = %s", (session_uuid,))
            else:
                session_uuid = f"{test_mode[:3]}_{req.participant_code}_{int(datetime.now().timestamp())}"
                cursor.execute("""
                INSERT INTO telemetry_sessions (
                    session_uuid, participant_code, test_mode,
                    cinema_id, cinema_name, movie_id, movie_title,
                    started_at, ended_at, total_duration_seconds,
                    is_completed, max_step_reached, total_errors, taps_count,
                    notes, device_info
                ) VALUES (%s, %s, %s, 'app-oficial-cinemark', %s, 'app-oficial', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    session_uuid,
                    req.participant_code,
                    test_mode,
                    req.cinema_name or "Cinemark Mallplaza Trujillo (App Oficial)",
                    req.movie_title or "Evaluación App Oficial",
                    started_at,
                    started_at,
                    req.total_duration_seconds,
                    req.is_completed,
                    req.max_step_reached,
                    req.total_errors,
                    req.taps_count or 0,
                    req.notes or "",
                    f"Ficha de Observación ({test_mode}) - {req.notes or ''}"
                ))

            # 3. Registrar duraciones por etapa en un solo roundtrip
            if req.step_durations:
                step_items = [
                    (session_uuid, step_name, float(duration), 0, started_at, started_at)
                    for step_name, duration in req.step_durations.items()
                ]
                cursor.executemany("""
                INSERT INTO telemetry_step_durations (
                    session_uuid, step_name, duration_seconds, taps_count, started_at, ended_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """, step_items)

            # 4. Registrar errores observados en un solo roundtrip
            if req.errors:
                error_items = [
                    (
                        session_uuid,
                        err.get("step_name") or err.get("step") or "General",
                        err.get("error_type") or err.get("type") or "FallaObservada",
                        err.get("description") or "",
                        started_at
                    )
                    for err in req.errors
                ]
                cursor.executemany("""
                INSERT INTO telemetry_errors (
                    session_uuid, step_name, error_type, description, occurred_at
                ) VALUES (%s, %s, %s, %s, %s)
                """, error_items)

            # 5. Si incluye respuestas SUS opcionales
            sus_score = None
            adjective = None
            if req.sus_survey and all(f"q{i}" in req.sus_survey for i in range(1, 11)):
                q_vals = [int(req.sus_survey[f"q{i}"]) for i in range(1, 11)]
                sus_score, adjective = TelemetryService.calculate_sus_score(*q_vals)
                cursor.execute("""
                INSERT INTO sus_survey_responses (
                    session_uuid, participant_code, test_mode,
                    q1, q2, q3, q4, q5, q6, q7, q8, q9, q10,
                    sus_score, adjective_rating, comments
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    session_uuid,
                    req.participant_code,
                    test_mode,
                    *q_vals,
                    sus_score,
                    adjective,
                    req.sus_survey.get("comments") or req.notes
                ))

            logger.info(f"Ficha de observación guardada con éxito para {req.participant_code} ({test_mode})")
            return {
                "status": "ok",
                "session_uuid": session_uuid,
                "participant_code": req.participant_code,
                "test_mode": test_mode,
                "total_duration_seconds": req.total_duration_seconds,
                "total_errors": req.total_errors,
                "sus_score": sus_score,
                "adjective_rating": adjective
            }

    @staticmethod
    def check_database_health() -> Dict[str, Any]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM telemetry_sessions")
            sess_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) as count FROM participants")
            part_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) as count FROM telemetry_step_durations")
            steps_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) as count FROM telemetry_errors")
            errors_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) as count FROM sus_survey_responses")
            sus_count = cursor.fetchone()["count"]

            return {
                "status": "connected",
                "sessions_count": sess_count,
                "participants_count": part_count,
                "steps_count": steps_count,
                "errors_count": errors_count,
                "sus_count": sus_count,
            }

