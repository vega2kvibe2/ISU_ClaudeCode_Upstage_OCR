from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

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

# 라우터 등록 (Phase 2~3에서 구현)
# from routers import upload, expenses, summary
# app.include_router(upload.router, prefix="/api")
# app.include_router(expenses.router, prefix="/api")
# app.include_router(summary.router, prefix="/api")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Receipt Tracker API is running"}
