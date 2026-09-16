import io
import csv
from typing import Optional, Dict, Any
from ..core.database import get_db_cursor
from ..models.schemas import AnalyticsSummaryResponse

class AnalyticsService:
    @staticmethod
    def get_summary(test_mode: Optional[str] = None) -> AnalyticsSummaryResponse:
        where_clause = "WHERE test_mode = %s" if test_mode else ""
        params = (test_mode,) if test_mode else ()

        with get_db_cursor() as cursor:
            # 1. Total sesiones y completadas (Eficacia)
            cursor.execute(f"""
            SELECT 
                COUNT(*) as total_sessions,
                SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_sessions,
                AVG(total_duration_seconds) as avg_duration,
                SUM(total_errors) as total_errors
            FROM telemetry_sessions
            {where_clause}
            """, params)
            session_stats = cursor.fetchone() or {}

            total_sessions = int(session_stats.get("total_sessions") or 0)
            completed_sessions = int(session_stats.get("completed_sessions") or 0)
            avg_duration = float(session_stats.get("avg_duration") or 0.0)
            total_errors = int(session_stats.get("total_errors") or 0)
            completion_rate = (float(completed_sessions) / float(total_sessions) * 100.0) if total_sessions > 0 else 0.0

            # 2. Promedio por etapa (Eficiencia)
            step_join = f"JOIN telemetry_sessions s ON d.session_uuid = s.session_uuid WHERE s.test_mode = %s" if test_mode else ""
            cursor.execute(f"""
            SELECT 
                d.step_name,
                AVG(d.duration_seconds) as avg_step_duration
            FROM telemetry_step_durations d
            {step_join}
            GROUP BY d.step_name
            """, params)
            step_rows = cursor.fetchall()
            avg_step_durations: Dict[str, float] = {
                r["step_name"]: round(float(r["avg_step_duration"]), 2)
                for r in step_rows
            }

            # 3. Errores agrupados por tipo y por etapa (Eficacia)
            err_join = f"JOIN telemetry_sessions s ON e.session_uuid = s.session_uuid WHERE s.test_mode = %s" if test_mode else ""
            cursor.execute(f"""
            SELECT error_type, COUNT(*) as qty
            FROM telemetry_errors e
            {err_join}
            GROUP BY error_type
            """, params)
            errors_by_type = {r["error_type"]: int(r["qty"]) for r in cursor.fetchall()}

            cursor.execute(f"""
            SELECT step_name, COUNT(*) as qty
            FROM telemetry_errors e
            {err_join}
            GROUP BY step_name
            """, params)
            errors_by_step = {r["step_name"]: int(r["qty"]) for r in cursor.fetchall()}

            # 4. Métricas SUS (Satisfacción)
            sus_where = "WHERE test_mode = %s" if test_mode else ""
            cursor.execute(f"""
            SELECT 
                COUNT(*) as sus_count,
                AVG(sus_score) as avg_sus
            FROM sus_survey_responses
            {sus_where}
            """, params)
            sus_stats = cursor.fetchone() or {}
            sus_count = sus_stats.get("sus_count") or 0
            avg_sus = round(float(sus_stats.get("avg_sus")), 2) if sus_stats.get("avg_sus") is not None else None

            return AnalyticsSummaryResponse(
                total_sessions=total_sessions,
                completed_sessions=completed_sessions,
                completion_rate_percent=round(completion_rate, 2),
                avg_total_duration_seconds=round(avg_duration, 2),
                avg_step_durations=avg_step_durations,
                total_errors_recorded=total_errors,
                errors_by_type=errors_by_type,
                errors_by_step=errors_by_step,
                sus_score_avg=avg_sus,
                sus_responses_count=sus_count
            )

    @staticmethod
    def export_sessions_csv(test_mode: Optional[str] = None) -> str:
        where_clause = "WHERE test_mode = %s" if test_mode else ""
        params = (test_mode,) if test_mode else ()

        with get_db_cursor() as cursor:
            cursor.execute(f"""
            SELECT 
                session_uuid, participant_code, test_mode,
                cinema_name, movie_title, started_at, ended_at,
                total_duration_seconds, is_completed, max_step_reached, total_errors
            FROM telemetry_sessions
            {where_clause}
            ORDER BY created_at DESC
            """, params)
            rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "session_uuid", "participant_code", "test_mode", "cinema_name",
            "movie_title", "started_at", "ended_at", "total_duration_seconds",
            "is_completed", "max_step_reached", "total_errors"
        ])
        for r in rows:
            writer.writerow([
                r["session_uuid"], r["participant_code"], r["test_mode"],
                r["cinema_name"], r["movie_title"], r["started_at"], r["ended_at"],
                r["total_duration_seconds"], 1 if r["is_completed"] else 0,
                r["max_step_reached"], r["total_errors"]
            ])
        return output.getvalue()

    @staticmethod
    def export_sus_csv(test_mode: Optional[str] = None) -> str:
        where_clause = "WHERE test_mode = %s" if test_mode else ""
        params = (test_mode,) if test_mode else ()

        with get_db_cursor() as cursor:
            cursor.execute(f"""
            SELECT 
                id, session_uuid, participant_code, test_mode,
                q1, q2, q3, q4, q5, q6, q7, q8, q9, q10,
                sus_score, adjective_rating, comments, submitted_at
            FROM sus_survey_responses
            {where_clause}
            ORDER BY submitted_at DESC
            """, params)
            rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "session_uuid", "participant_code", "test_mode",
            "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "q10",
            "sus_score", "adjective_rating", "comments", "submitted_at"
        ])
        for r in rows:
            writer.writerow([
                r["id"], r["session_uuid"], r["participant_code"], r["test_mode"],
                r["q1"], r["q2"], r["q3"], r["q4"], r["q5"],
                r["q6"], r["q7"], r["q8"], r["q9"], r["q10"],
                r["sus_score"], r["adjective_rating"], r["comments"], r["submitted_at"]
            ])
        return output.getvalue()

    @staticmethod
    def export_step_durations_csv(test_mode: Optional[str] = None) -> str:
        where_clause = "WHERE s.test_mode = %s" if test_mode else ""
        params = (test_mode,) if test_mode else ()

        with get_db_cursor() as cursor:
            cursor.execute(f"""
            SELECT 
                d.id, d.session_uuid, s.participant_code, s.test_mode,
                d.step_name, d.duration_seconds, d.started_at, d.ended_at
            FROM telemetry_step_durations d
            JOIN telemetry_sessions s ON d.session_uuid = s.session_uuid
            {where_clause}
            ORDER BY d.created_at ASC
            """, params)
            rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "session_uuid", "participant_code", "test_mode",
            "step_name", "duration_seconds", "started_at", "ended_at"
        ])
        for r in rows:
            writer.writerow([
                r["id"], r["session_uuid"], r["participant_code"], r["test_mode"],
                r["step_name"], r["duration_seconds"], r["started_at"], r["ended_at"]
            ])
        return output.getvalue()
