from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Esquemas de Telemetría ---

class SessionStartRequest(BaseModel):
    session_uuid: str
    participant_code: Optional[str] = "ANONIMO"
    test_mode: Optional[str] = "posttest" # pretest o posttest
    cinema_id: Optional[str] = None
    cinema_name: Optional[str] = None
    movie_id: Optional[str] = None
    movie_title: Optional[str] = None
    device_info: Optional[str] = None
    started_at: Optional[datetime] = Field(default_factory=datetime.now)

class StepDurationEvent(BaseModel):
    session_uuid: str
    step_name: str
    duration_seconds: float
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = Field(default_factory=datetime.now)

class ErrorEvent(BaseModel):
    session_uuid: str
    step_name: str
    error_type: str
    description: Optional[str] = None
    occurred_at: Optional[datetime] = Field(default_factory=datetime.now)

class SessionCompleteRequest(BaseModel):
    session_uuid: str
    is_completed: bool = True
    max_step_reached: str
    total_duration_seconds: float
    ended_at: Optional[datetime] = Field(default_factory=datetime.now)

class SessionFullSyncRequest(BaseModel):
    session_uuid: str
    participant_code: Optional[str] = "ANONIMO"
    test_mode: Optional[str] = "posttest"
    cinema_id: Optional[str] = None
    cinema_name: Optional[str] = None
    movie_id: Optional[str] = None
    movie_title: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_duration_seconds: float
    is_completed: bool = True
    max_step_reached: str
    device_info: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

# --- Esquemas de Encuesta SUS (Satisfacción del Usuario) ---

class SusSurveyRequest(BaseModel):
    session_uuid: Optional[str] = None
    participant_code: str = "ANONIMO"
    test_mode: str = "posttest" # pretest o posttest
    # 10 preguntas de la escala SUS (1 a 5)
    q1: int = Field(..., ge=1, le=5, description="Me gustaría usar este sistema con frecuencia")
    q2: int = Field(..., ge=1, le=5, description="Encontré el sistema innecesariamente complejo")
    q3: int = Field(..., ge=1, le=5, description="Pensé que el sistema era fácil de usar")
    q4: int = Field(..., ge=1, le=5, description="Necesitaría el apoyo de un técnico para usarlo")
    q5: int = Field(..., ge=1, le=5, description="Las funciones del sistema estaban bien integradas")
    q6: int = Field(..., ge=1, le=5, description="Había demasiada inconsistencia en el sistema")
    q7: int = Field(..., ge=1, le=5, description="La gente aprendería a usarlo muy rápidamente")
    q8: int = Field(..., ge=1, le=5, description="Encontré el sistema muy engorroso de usar")
    q9: int = Field(..., ge=1, le=5, description="Me sentí muy seguro/a usando el sistema")
    q10: int = Field(..., ge=1, le=5, description="Necesité aprender muchas cosas antes de usarlo")
    comments: Optional[str] = None

class SusSurveyResponse(BaseModel):
    id: int
    participant_code: str
    test_mode: str
    sus_score: float
    adjective_rating: str
    submitted_at: datetime

# --- Esquemas de Respuesta y Analítica para Resultados ---

class AnalyticsSummaryResponse(BaseModel):
    total_sessions: int
    completed_sessions: int
    completion_rate_percent: float
    avg_total_duration_seconds: float
    avg_step_durations: Dict[str, float]
    total_errors_recorded: int
    errors_by_type: Dict[str, int]
    errors_by_step: Dict[str, int]
    sus_score_avg: Optional[float] = None
    sus_responses_count: int = 0
