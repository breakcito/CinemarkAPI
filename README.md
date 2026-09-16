# Crear entorno virtual
Zsh: python3 -m venv .venv
Powershell & CMD: python -m venv .venv

# Activar .venv
Zsh: source .venv/bin/activate
Powershell: .\.venv\Scripts\Activate.ps1
CMD: .\.venv\Scripts\activate.bat

# Ejecutar proyecto
fastapi dev src/main.py

# Instalar dependencias del proyecto
pip install -r requirements.txt

# Guardar dependencias
pip freeze > requirements.txt