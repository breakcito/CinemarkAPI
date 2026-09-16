import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from .config import settings
import logging

logger = logging.getLogger(__name__)

def get_connection():
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        cursorclass=DictCursor,
        autocommit=True,
        charset='utf8mb4',
        connect_timeout=10
    )

@contextmanager
def get_db_cursor():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
    finally:
        conn.close()

def init_db():
    logger.info("Verificando e inicializando tablas en MySQL para la tesis...")
    with get_db_cursor() as cursor:
        # 1. Tabla de Participantes del experimento
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INT AUTO_INCREMENT PRIMARY KEY,
            participant_code VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(100),
            age INT,
            gender VARCHAR(20),
            test_mode ENUM('pretest', 'posttest') DEFAULT 'posttest',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 2. Tabla de Sesiones de Compra y Telemetría
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_uuid VARCHAR(64) NOT NULL UNIQUE,
            participant_code VARCHAR(50) DEFAULT 'ANONIMO',
            test_mode VARCHAR(20) DEFAULT 'posttest',
            cinema_id VARCHAR(50),
            cinema_name VARCHAR(100),
            movie_id VARCHAR(50),
            movie_title VARCHAR(150),
            started_at DATETIME NOT NULL,
            ended_at DATETIME NULL,
            total_duration_seconds FLOAT DEFAULT 0.0,
            is_completed BOOLEAN DEFAULT FALSE,
            max_step_reached VARCHAR(50) DEFAULT 'Splash',
            total_errors INT DEFAULT 0,
            device_info TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_session_uuid (session_uuid),
            INDEX idx_participant_code (participant_code),
            INDEX idx_test_mode (test_mode)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 3. Tabla de Tiempos por Etapa Transaccional (Dimensión Eficiencia)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_step_durations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_uuid VARCHAR(64) NOT NULL,
            step_name VARCHAR(50) NOT NULL,
            duration_seconds FLOAT NOT NULL,
            started_at DATETIME NULL,
            ended_at DATETIME NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_step_session (session_uuid),
            INDEX idx_step_name (step_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 4. Tabla de Errores e Incidencias (Dimensión Eficacia)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_errors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_uuid VARCHAR(64) NOT NULL,
            step_name VARCHAR(50) NOT NULL,
            error_type VARCHAR(100) NOT NULL,
            description TEXT,
            occurred_at DATETIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_err_session (session_uuid),
            INDEX idx_err_type (error_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 5. Tabla de Cuestionario SUS (Dimensión Satisfacción del Usuario)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sus_survey_responses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_uuid VARCHAR(64) NULL,
            participant_code VARCHAR(50) NOT NULL,
            test_mode VARCHAR(20) DEFAULT 'posttest',
            q1 INT NOT NULL,
            q2 INT NOT NULL,
            q3 INT NOT NULL,
            q4 INT NOT NULL,
            q5 INT NOT NULL,
            q6 INT NOT NULL,
            q7 INT NOT NULL,
            q8 INT NOT NULL,
            q9 INT NOT NULL,
            q10 INT NOT NULL,
            sus_score FLOAT NOT NULL,
            adjective_rating VARCHAR(50) NOT NULL,
            comments TEXT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sus_participant (participant_code),
            INDEX idx_sus_mode (test_mode)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        logger.info("Tablas de MySQL verificadas y listas con éxito.")
