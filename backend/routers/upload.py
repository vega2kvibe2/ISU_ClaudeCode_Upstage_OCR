"""
POST /api/upload — 영수증 파일 업로드 및 OCR 파싱 라우터

처리 흐름:
  파일 검증 → 저장 → OCR 파싱 → expenses.json append 저장 → 결과 반환
"""
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.ocr_service import process_receipt

router = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
DATA_FILE = Path(__file__).parent.parent / "data" / "expenses.json"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

UPLOAD_DIR.mkdir(exist_ok=True)
DATA_FILE.parent.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_receipt(file: UploadFile = File(...)):
    """
    영수증 이미지(JPG/PNG) 또는 PDF를 업로드하면 OCR 파싱 후 지출 데이터를 반환합니다.

    - 지원 형식: JPG, PNG, PDF
    - 최대 크기: 10MB
    """
    # 1. 파일 확장자 검증
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 파일 형식입니다. JPG, PNG, PDF만 허용됩니다.",
        )

    # 2. 파일 읽기 및 크기 검증 (10MB 초과 시 400)
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="파일 크기가 10MB를 초과합니다.",
        )

    # 3. 파일 저장 (UUID 기반 파일명)
    file_id = str(uuid.uuid4())
    save_filename = f"{file_id}{ext}"
    save_path = UPLOAD_DIR / save_filename
    save_path.write_bytes(file_bytes)

    # 4. OCR 파싱
    content_type = file.content_type or "application/octet-stream"
    try:
        parsed = await process_receipt(file_bytes, file.filename or save_filename, content_type)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"OCR 파싱 실패: {str(e)}")

    # 5. expenses.json에 append 저장
    expense = {
        "id": file_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw_image_path": f"uploads/{save_filename}",
        "store_name": parsed.get("store_name", ""),
        "receipt_date": parsed.get("receipt_date", ""),
        "receipt_time": parsed.get("receipt_time"),
        "category": parsed.get("category", "기타"),
        "items": parsed.get("items", []),
        "subtotal": parsed.get("subtotal", 0),
        "discount": parsed.get("discount", 0),
        "tax": parsed.get("tax", 0),
        "total_amount": parsed.get("total_amount", 0),
        "payment_method": parsed.get("payment_method"),
    }

    expenses: list = []
    if DATA_FILE.exists():
        try:
            expenses = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            expenses = []

    expenses.append(expense)
    DATA_FILE.write_text(
        json.dumps(expenses, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return expense
