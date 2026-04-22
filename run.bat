@echo off
if not exist .venv (
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
  python ml\generate_data.py
  python ml\train.py
) else (
  call .venv\Scripts\activate.bat
)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
