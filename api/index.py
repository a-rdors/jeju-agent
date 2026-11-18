"""Vercel 배포용 입구. Vercel이 이 파일의 `app`(FastAPI)을 서버로 실행한다.

실제 코드는 server/api.py. 로컬 실행은 그대로:
    .venv/Scripts/python -m uvicorn server.api:app --port 8000
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.api import app  # noqa: E402,F401
