import sys
from pathlib import Path

# backend/ 디렉토리를 sys.path에 추가
# → `cd backend && uvicorn main:app` 와 `uvicorn backend.main:app` 양쪽 호환
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

app = FastAPI(
    title="Receipt Expense Tracker API",
    description="영수증 OCR 기반 지출 관리 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from routers import upload
app.include_router(upload.router, prefix="/api")
# Phase 3에서 추가
# from routers import expenses, summary
# app.include_router(expenses.router, prefix="/api")
# app.include_router(summary.router, prefix="/api")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Receipt Tracker API is running"}
