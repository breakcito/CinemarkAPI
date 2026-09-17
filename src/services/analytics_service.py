import io
import csv
from typing import Optional, Dict, Any, List
from ..core.database import get_db_cursor
from ..models.schemas import AnalyticsSummaryResponse, WilcoxonPairItem, WilcoxonMatrixResponse

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

    @staticmethod
    def get_wilcoxon_matrix() -> WilcoxonMatrixResponse:
        """
        Construye la matriz pareada (Pretest vs Posttest) por participante
        para el contraste estadístico de Wilcoxon para muestras relacionadas.
        """
        with get_db_cursor() as cursor:
            # 1. Obtener lista de participantes únicos registrados
            cursor.execute("""
            SELECT p.participant_code, p.name, p.age, p.gender, p.cinema_frequency
            FROM participants p
            UNION
            SELECT DISTINCT participant_code, 'Participante', NULL, NULL, NULL
            FROM telemetry_sessions
            WHERE participant_code != 'ANONIMO'
            ORDER BY participant_code ASC
            """)
            raw_participants = cursor.fetchall()
            part_dict: Dict[str, Dict[str, Any]] = {}
            for p in raw_participants:
                code = p["participant_code"]
                if code not in part_dict or (p.get("age") is not None):
                    part_dict[code] = p
            participants = list(part_dict.values())

            # 2. Consultar sesiones por test_mode
            cursor.execute("""
            SELECT session_uuid, participant_code, test_mode, total_duration_seconds,
                   is_completed, total_errors, taps_count, created_at
            FROM telemetry_sessions
            WHERE participant_code != 'ANONIMO'
            ORDER BY created_at DESC
            """)
            all_sessions = cursor.fetchall()

            # 3. Consultar respuestas SUS
            cursor.execute("""
            SELECT participant_code, test_mode, sus_score, adjective_rating
            FROM sus_survey_responses
            WHERE participant_code != 'ANONIMO'
            ORDER BY submitted_at DESC
            """)
            all_sus = cursor.fetchall()

            # 4. Consultar tiempos por etapa
            cursor.execute("""
            SELECT d.session_uuid, s.participant_code, s.test_mode, d.step_name, d.duration_seconds
            FROM telemetry_step_durations d
            JOIN telemetry_sessions s ON d.session_uuid = s.session_uuid
            WHERE s.participant_code != 'ANONIMO'
            """)
            all_steps = cursor.fetchall()

        # Agrupar sesiones por participante y test_mode (tomando la más reciente)
        session_map: Dict[str, Dict[str, Any]] = {}
        for s in all_sessions:
            key = f"{s['participant_code']}_{s['test_mode']}"
            if key not in session_map:
                session_map[key] = s

        # Agrupar SUS por participante y test_mode
        sus_map: Dict[str, Dict[str, Any]] = {}
        for su in all_sus:
            key = f"{su['participant_code']}_{su['test_mode']}"
            if key not in sus_map:
                sus_map[key] = su

        # Agrupar pasos por sesión
        step_map: Dict[str, Dict[str, float]] = {}
        for st in all_steps:
            uuid = st["session_uuid"]
            if uuid not in step_map:
                step_map[uuid] = {}
            step_map[uuid][st["step_name"]] = round(float(st["duration_seconds"]), 2)

        paired_items: List[WilcoxonPairItem] = []
        pre_times = []
        post_times = []
        pre_errors_list = []
        post_errors_list = []
        pre_sus_list = []
        post_sus_list = []

        for p in participants:
            p_code = p["participant_code"]
            pre_sess = session_map.get(f"{p_code}_pretest")
            post_sess = session_map.get(f"{p_code}_posttest")

            # Solo incluir o evaluar si tiene al menos una sesión registrada
            if not pre_sess and not post_sess:
                continue

            pre_sus = sus_map.get(f"{p_code}_pretest")
            post_sus = sus_map.get(f"{p_code}_posttest")

            pre_time = float(pre_sess["total_duration_seconds"]) if pre_sess else None
            post_time = float(post_sess["total_duration_seconds"]) if post_sess else None
            diff_time = round(post_time - pre_time, 2) if (pre_time is not None and post_time is not None) else None
            pct_reduction = round(((pre_time - post_time) / pre_time) * 100.0, 2) if (pre_time and post_time and pre_time > 0) else None

            pre_err = int(pre_sess["total_errors"]) if pre_sess else None
            post_err = int(post_sess["total_errors"]) if post_sess else None
            diff_err = (post_err - pre_err) if (pre_err is not None and post_err is not None) else None

            pre_s_score = float(pre_sus["sus_score"]) if pre_sus else None
            post_s_score = float(post_sus["sus_score"]) if post_sus else None
            diff_sus = round(post_s_score - pre_s_score, 2) if (pre_s_score is not None and post_s_score is not None) else None

            pre_uuid = pre_sess["session_uuid"] if pre_sess else None
            post_uuid = post_sess["session_uuid"] if post_sess else None

            item = WilcoxonPairItem(
                participant_code=p_code,
                age=p.get("age"),
                gender=p.get("gender"),
                cinema_frequency=p.get("cinema_frequency"),
                pre_completed=bool(pre_sess["is_completed"]) if pre_sess else None,
                post_completed=bool(post_sess["is_completed"]) if post_sess else None,
                pre_errors=pre_err,
                post_errors=post_err,
                diff_errors=diff_err,
                pre_time_total_s=pre_time,
                post_time_total_s=post_time,
                diff_time_s=diff_time,
                pct_time_reduction=pct_reduction,
                pre_step_times=step_map.get(pre_uuid, {}) if pre_uuid else {},
                post_step_times=step_map.get(post_uuid, {}) if post_uuid else {},
                pre_sus_score=pre_s_score,
                post_sus_score=post_s_score,
                diff_sus_score=diff_sus,
                pre_sus_rating=pre_sus.get("adjective_rating") if pre_sus else None,
                post_sus_rating=post_sus.get("adjective_rating") if post_sus else None,
            )
            paired_items.append(item)

            if pre_time is not None: pre_times.append(pre_time)
            if post_time is not None: post_times.append(post_time)
            if pre_err is not None: pre_errors_list.append(pre_err)
            if post_err is not None: post_errors_list.append(post_err)
            if pre_s_score is not None: pre_sus_list.append(pre_s_score)
            if post_s_score is not None: post_sus_list.append(post_s_score)

        return WilcoxonMatrixResponse(
            total_paired_participants=len(paired_items),
            data=paired_items,
            mean_pre_time=round(sum(pre_times)/len(pre_times), 2) if pre_times else 0.0,
            mean_post_time=round(sum(post_times)/len(post_times), 2) if post_times else 0.0,
            mean_pre_errors=round(sum(pre_errors_list)/len(pre_errors_list), 2) if pre_errors_list else 0.0,
            mean_post_errors=round(sum(post_errors_list)/len(post_errors_list), 2) if post_errors_list else 0.0,
            mean_pre_sus=round(sum(pre_sus_list)/len(pre_sus_list), 2) if pre_sus_list else None,
            mean_post_sus=round(sum(post_sus_list)/len(post_sus_list), 2) if post_sus_list else None,
        )

    @staticmethod
    def export_wilcoxon_csv() -> str:
        """
        Exporta directamente el dataset pareado Pretest vs Posttest en formato CSV
        listo para ser procesado por SPSS, R o Python con scipy.stats.wilcoxon.
        """
        matrix = AnalyticsService.get_wilcoxon_matrix()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "participante", "edad", "genero", "frecuencia_cine",
            "pre_completitud", "post_completitud",
            "pre_errores", "post_errores", "dif_errores",
            "pre_tiempo_total_s", "post_tiempo_total_s", "dif_tiempo_s", "pct_reduccion_tiempo",
            "pre_tiempo_home_s", "post_tiempo_home_s",
            "pre_tiempo_horarios_s", "post_tiempo_horarios_s",
            "pre_tiempo_tickets_s", "post_tiempo_tickets_s",
            "pre_tiempo_asientos_s", "post_tiempo_asientos_s",
            "pre_tiempo_confiteria_s", "post_tiempo_confiteria_s",
            "pre_tiempo_pago_s", "post_tiempo_pago_s",
            "pre_sus_score", "post_sus_score", "dif_sus_score",
            "pre_sus_adjetivo", "post_sus_adjetivo"
        ])

        for it in matrix.data:
            pre_steps = it.pre_step_times
            post_steps = it.post_step_times

            writer.writerow([
                it.participant_code,
                it.age or "",
                it.gender or "",
                it.cinema_frequency or "",
                1 if it.pre_completed else (0 if it.pre_completed is not None else ""),
                1 if it.post_completed else (0 if it.post_completed is not None else ""),
                it.pre_errors if it.pre_errors is not None else "",
                it.post_errors if it.post_errors is not None else "",
                it.diff_errors if it.diff_errors is not None else "",
                it.pre_time_total_s if it.pre_time_total_s is not None else "",
                it.post_time_total_s if it.post_time_total_s is not None else "",
                it.diff_time_s if it.diff_time_s is not None else "",
                it.pct_time_reduction if it.pct_time_reduction is not None else "",
                pre_steps.get("Home", ""), post_steps.get("Home", ""),
                pre_steps.get("Showtimes", pre_steps.get("Horarios", "")), post_steps.get("Showtimes", post_steps.get("Horarios", "")),
                pre_steps.get("Tickets", ""), post_steps.get("Tickets", ""),
                pre_steps.get("Seats", pre_steps.get("Asientos", "")), post_steps.get("Seats", post_steps.get("Asientos", "")),
                pre_steps.get("Concessions", pre_steps.get("Confitería", "")), post_steps.get("Concessions", post_steps.get("Confitería", "")),
                pre_steps.get("Payment", pre_steps.get("Pago", "")), post_steps.get("Payment", post_steps.get("Pago", "")),
                it.pre_sus_score if it.pre_sus_score is not None else "",
                it.post_sus_score if it.post_sus_score is not None else "",
                it.diff_sus_score if it.diff_sus_score is not None else "",
                it.pre_sus_rating or "",
                it.post_sus_rating or ""
            ])

        return output.getvalue()
