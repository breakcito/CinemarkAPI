import uuid
import time
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_full_telemetry_and_survey_flow():
    session_id = f"test-{uuid.uuid4()}"
    participant = "TEST-USER-001"

    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    print("✓ Health check OK")

    # 2. Iniciar Sesión
    start_payload = {
        "session_uuid": session_id,
        "participant_code": participant,
        "test_mode": "posttest",
        "cinema_id": "mallplaza_trujillo",
        "cinema_name": "Cinemark Mallplaza Trujillo",
        "movie_id": "m1",
        "movie_title": "Dune: Parte Dos",
        "device_info": "Test Runner / Python TestClient"
    }
    res = client.post("/api/v1/telemetry/session/start", json=start_payload)
    assert res.status_code == 201
    assert res.json()["status"] == "ok"
    print("✓ Sesión iniciada")

    # 3. Registrar pasos de compra (Eficiencia)
    steps = [
        ("Splash", 1.8),
        ("Home", 5.2),
        ("Showtimes", 8.4),
        ("Tickets", 6.1)
    ]
    for step_name, duration in steps:
        step_payload = {
            "session_uuid": session_id,
            "step_name": step_name,
            "duration_seconds": duration
        }
        res = client.post("/api/v1/telemetry/session/step", json=step_payload)
        assert res.status_code == 200
    print("✓ Pasos registrados correctamente")

    # 4. Registrar un error o incidencia de usuario (Eficacia)
    error_payload = {
        "session_uuid": session_id,
        "step_name": "Tickets",
        "error_type": "CouponInvalid",
        "description": "El usuario ingresó un código expirado o erróneo"
    }
    res = client.post("/api/v1/telemetry/session/error", json=error_payload)
    assert res.status_code == 200
    print("✓ Error registrado correctamente")

    # 5. Finalizar sesión
    complete_payload = {
        "session_uuid": session_id,
        "is_completed": True,
        "max_step_reached": "Tickets",
        "total_duration_seconds": 21.5
    }
    res = client.post("/api/v1/telemetry/session/complete", json=complete_payload)
    assert res.status_code == 200
    print("✓ Sesión finalizada correctamente")

    # 6. Enviar encuesta SUS (Satisfacción)
    # Calificaciones positivas (alto acuerdo en impares, bajo en pares)
    # Impares: 5, 5, 5, 5, 5 -> (5-1)*5 = 20
    # Pares: 1, 1, 1, 1, 1 -> (5-1)*5 = 20
    # Total: (20 + 20) * 2.5 = 100.0
    sus_payload = {
        "session_uuid": session_id,
        "participant_code": participant,
        "test_mode": "posttest",
        "q1": 5, "q2": 1, "q3": 5, "q4": 1, "q5": 5,
        "q6": 1, "q7": 5, "q8": 1, "q9": 5, "q10": 1,
        "comments": "Excelente flujo, muy claro el contador y los tickets."
    }
    res = client.post("/api/v1/survey/sus", json=sus_payload)
    assert res.status_code == 201
    sus_res = res.json()
    assert sus_res["sus_score"] == 100.0
    assert "Excelente" in sus_res["adjective_rating"]
    print(f"✓ Encuesta SUS calculada: {sus_res['sus_score']} pts ({sus_res['adjective_rating']})")

    # 7. Resumen de resultados (Métricas para Tesis)
    res = client.get("/api/v1/analytics/summary?test_mode=posttest")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_sessions"] > 0
    assert summary["completion_rate_percent"] > 0
    assert "Tickets" in summary["avg_step_durations"]
    assert "CouponInvalid" in summary["errors_by_type"]
    assert summary["sus_score_avg"] is not None
    print("✓ Resumen de resultados analíticos validado:")
    print(f"  - Total sesiones: {summary['total_sessions']}")
    print(f"  - Tasa de éxito: {summary['completion_rate_percent']}%")
    print(f"  - Promedio SUS: {summary['sus_score_avg']}")

    # 8. Exportación CSV
    res_csv = client.get("/api/v1/analytics/export/sessions.csv")
    assert res_csv.status_code == 200
    assert "session_uuid,participant_code" in res_csv.text
    print("✓ Exportación CSV funcionando")

if __name__ == "__main__":
    test_full_telemetry_and_survey_flow()
    print("\nTODOS LOS TESTS DE TELEMETRÍA Y ANALÍTICA PASARON CON ÉXITO.")
