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
    taps_count: Optional[int] = 0
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
    participant_code: Optional[str] = None
    is_completed: bool = True
    max_step_reached: str
    total_duration_seconds: float
    taps_count: Optional[int] = 0
    total_errors: Optional[int] = None
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
    taps_count: Optional[int] = 0
    is_completed: bool = True
    max_step_reached: str
    device_info: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

# --- Esquemas de Participantes de Tesis ---

class ParticipantCreateRequest(BaseModel):
    participant_code: str
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    cinema_frequency: Optional[str] = None # Semanal, Quincenal, Mensual, Ocasional
    notes: Optional[str] = None

class ParticipantResponse(BaseModel):
    id: int
    participant_code: str
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    cinema_frequency: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

# --- Esquema de Ficha de Observación (Pretest y Posttest) ---

class ObservationErrorItem(BaseModel):
    step_name: str
    error_type: str
    description: Optional[str] = ""

class PretestObservationRequest(BaseModel):
    participant_code: str
    test_mode: Optional[str] = "pretest"
    cinema_name: Optional[str] = "Cinemark Mallplaza Trujillo (App Oficial)"
    movie_title: Optional[str] = "Película evaluada en App Oficial"
    total_duration_seconds: float
    is_completed: bool = True
    max_step_reached: str = "Historial"
    total_errors: int = 0
    taps_count: Optional[int] = 0
    step_durations: Optional[Dict[str, float]] = None # ej: {"Inicio": 25.0, "Horarios": 40.0, "Tickets": 50.0, ...}
    errors: Optional[List[Dict[str, Any]]] = None # ej: [{"step_name": "Asientos", "error_type": "ZoomButacas", "description": "..."}]
    sus_survey: Optional[Dict[str, Any]] = None # {"q1": 3, "q2": 4, ..., "comments": "..."}
    notes: Optional[str] = None

class ObservationSheetResponse(BaseModel):
    found: bool
    participant_code: str
    test_mode: str
    session_uuid: Optional[str] = None
    is_completed: bool = True
    max_step_reached: str = "Historial"
    total_duration_seconds: float = 0.0
    total_errors: int = 0
    taps_count: int = 0
    step_durations: Dict[str, float] = {}
    errors: List[ObservationErrorItem] = []
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class ParticipantActivateRequest(BaseModel):
    participant_code: str

class ParticipantEnrichedItem(BaseModel):
    id: int
    participant_code: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    cinema_frequency: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    is_active: bool = False
    last_active_at: Optional[datetime] = None
    has_pretest: bool = False
    has_posttest: bool = False
    has_comparative: bool = False
    pretest_time_s: Optional[float] = None
    posttest_time_s: Optional[float] = None
    pretest_errors: Optional[int] = None
    posttest_errors: Optional[int] = None
    pretest_completed: Optional[bool] = None
    posttest_completed: Optional[bool] = None


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

# --- Esquemas de Cuestionario Comparativo Simultáneo (Pretest vs Posttest) ---

class ComparativeSurveyRequest(BaseModel):
    participant_code: str
    # 10 preguntas para Pretest (App Oficial Cinemark)
    pre_q1: int = Field(..., ge=1, le=5)
    pre_q2: int = Field(..., ge=1, le=5)
    pre_q3: int = Field(..., ge=1, le=5)
    pre_q4: int = Field(..., ge=1, le=5)
    pre_q5: int = Field(..., ge=1, le=5)
    pre_q6: int = Field(..., ge=1, le=5)
    pre_q7: int = Field(..., ge=1, le=5)
    pre_q8: int = Field(..., ge=1, le=5)
    pre_q9: int = Field(..., ge=1, le=5)
    pre_q10: int = Field(..., ge=1, le=5)
    # 10 preguntas para Posttest (Prototipo Mejorado)
    post_q1: int = Field(..., ge=1, le=5)
    post_q2: int = Field(..., ge=1, le=5)
    post_q3: int = Field(..., ge=1, le=5)
    post_q4: int = Field(..., ge=1, le=5)
    post_q5: int = Field(..., ge=1, le=5)
    post_q6: int = Field(..., ge=1, le=5)
    post_q7: int = Field(..., ge=1, le=5)
    post_q8: int = Field(..., ge=1, le=5)
    post_q9: int = Field(..., ge=1, le=5)
    post_q10: int = Field(..., ge=1, le=5)
    # Preguntas heurísticas específicas de la tesis (1 a 5)
    heuristic_error_pre: Optional[int] = Field(default=3, ge=1, le=5)
    heuristic_error_post: Optional[int] = Field(default=5, ge=1, le=5)
    heuristic_seats_pre: Optional[int] = Field(default=3, ge=1, le=5)
    heuristic_seats_post: Optional[int] = Field(default=5, ge=1, le=5)
    heuristic_timer_pre: Optional[int] = Field(default=2, ge=1, le=5)
    heuristic_timer_post: Optional[int] = Field(default=5, ge=1, le=5)
    preferred_system: Optional[str] = "Prototipo"
    comments: Optional[str] = None

class ComparativeSurveyResponse(BaseModel):
    participant_code: str
    pre_sus_score: float
    post_sus_score: float
    diff_sus_score: float
    pct_improvement: float
    pre_adjective: str
    post_adjective: str
    submitted_at: datetime
    message: str

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

class WilcoxonPairItem(BaseModel):
    participant_code: str
    age: Optional[int] = None
    gender: Optional[str] = None
    cinema_frequency: Optional[str] = None
    # Eficacia
    pre_completed: Optional[bool] = None
    post_completed: Optional[bool] = None
    pre_errors: Optional[int] = None
    post_errors: Optional[int] = None
    diff_errors: Optional[int] = None
    # Eficiencia
    pre_time_total_s: Optional[float] = None
    post_time_total_s: Optional[float] = None
    diff_time_s: Optional[float] = None
    pct_time_reduction: Optional[float] = None
    # Tiempos por etapa
    pre_step_times: Dict[str, float] = {}
    post_step_times: Dict[str, float] = {}
    # Satisfacción SUS
    pre_sus_score: Optional[float] = None
    post_sus_score: Optional[float] = None
    diff_sus_score: Optional[float] = None
    pre_sus_rating: Optional[str] = None
    post_sus_rating: Optional[str] = None

class WilcoxonMatrixResponse(BaseModel):
    total_paired_participants: int
    data: List[WilcoxonPairItem]
    mean_pre_time: float
    mean_post_time: float
    mean_pre_errors: float
    mean_post_errors: float
    mean_pre_sus: Optional[float] = None
    mean_post_sus: Optional[float] = None
