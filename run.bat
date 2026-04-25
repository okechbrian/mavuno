@echo off
if not exist .venv2 (
  python -m venv .venv2
  call .venv2\Scripts\activate.bat
  pip install -r requirements.txt
  pip install -r ml\requirements-ml.txt
  python ml\generate_data.py
  python ml\train.py
) else (
  call .venv2\Scripts\activate.bat
)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
