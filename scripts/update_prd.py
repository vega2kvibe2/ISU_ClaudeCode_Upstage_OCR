#!/usr/bin/env python3
"""
PRD 체크박스 자동 업데이트 스크립트
백엔드/프론트엔드 파일 존재 여부와 내용을 검사하여
PRD_영수증_지출관리앱.md 의 완료 기준 체크박스를 자동으로 업데이트합니다.

Stop hook에서 호출됩니다: 매번 Claude가 응답을 완료할 때 실행됩니다.
"""
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRD_FILE = os.path.join(PROJECT_ROOT, "PRD_영수증_지출관리앱.md")


def fexists(*parts):
    """PROJECT_ROOT 기준 파일/디렉토리 존재 여부"""
    return os.path.exists(os.path.join(PROJECT_ROOT, *parts))


def fcontains(path, text):
    """파일에 특정 문자열 포함 여부"""
    try:
        with open(os.path.join(PROJECT_ROOT, path), encoding="utf-8") as f:
            return text in f.read()
    except Exception:
        return False


def safe_check(fn):
    try:
        return bool(fn())
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# 완료 기준 매핑: {PRD에 포함된 고유 문자열 일부: 판별 함수}
# 체크박스 라인에 이 문자열이 포함돼 있으면 조건 함수를 실행하여
# True 이면 [ ] → [x] 로 변경합니다.
# ─────────────────────────────────────────────────────────────
CRITERIA = {
    # Phase 1 ─ 프로젝트 환경 설정
    "uvicorn backend.main:app --reload` 실행 시 FastAPI 서버가 정상 기동된다": lambda: (
        fexists("backend", "main.py") and fexists("venv")
    ),
    "http://localhost:8000/docs` Swagger UI가 열린다": lambda: fexists("backend", "main.py"),
    ".env` 파일이 `.gitignore`에 포함되어 있다": lambda: (
        fexists(".gitignore") and fcontains(".gitignore", ".env")
    ),

    # Phase 2 ─ OCR 업로드 API
    "curl -X POST /api/upload -F": lambda: fexists("backend", "routers", "upload.py"),
    "10MB 초과 파일 업로드 시 400 오류가 반환된다": lambda: (
        fexists("backend", "routers", "upload.py")
        and fcontains("backend/routers/upload.py", "10")
    ),
    "PDF 파일 업로드 시 정상적으로 파싱된다": lambda: fexists("backend", "services", "ocr_service.py"),

    # Phase 3 ─ 부가 API
    "Postman으로 5개 엔드포인트": lambda: all([
        fexists("backend", "routers", "upload.py"),
        fexists("backend", "routers", "expenses.py"),
        fexists("backend", "routers", "summary.py"),
    ]),
    "GET /api/expenses?from=": lambda: (
        fexists("backend", "routers", "expenses.py")
        and fcontains("backend/routers/expenses.py", "from")
    ),
    "존재하지 않는 ID로 DELETE 시 404가 반환된다": lambda: (
        fexists("backend", "routers", "expenses.py")
        and fcontains("backend/routers/expenses.py", "404")
    ),

    # Phase 4 ─ 프론트엔드 환경 설정
    "npm run dev` 실행 시 `http://localhost:5173": lambda: fexists("frontend", "package.json"),
    "TailwindCSS 클래스가 정상 적용된다": lambda: fexists("frontend", "tailwind.config.js"),
    "`/`, `/upload`, `/expense/:id` 3개 경로가 라우팅된다": lambda: (
        fexists("frontend", "src", "App.jsx")
        and fcontains("frontend/src/App.jsx", "/upload")
        and fcontains("frontend/src/App.jsx", "/expense/")
    ),

    # Phase 5 ─ 업로드 화면
    "이미지를 드래그 앤 드롭하면 OCR 파싱이 실행된다": lambda: fexists("frontend", "src", "components", "DropZone.jsx"),
    "ProgressBar가 처리 중 표시되고 완료 후 숨겨진다": lambda: fexists("frontend", "src", "components", "ProgressBar.jsx"),
    "ParsePreview에서 필드를 수정하고 저장 시 대시보드로 이동한다": lambda: fexists("frontend", "src", "components", "ParsePreview.jsx"),
    "Toast 알림이 저장 성공 시 표시된다": lambda: fexists("frontend", "src", "components", "Toast.jsx"),

    # Phase 6 ─ 대시보드 화면
    "대시보드 진입 시 저장된 지출 내역이 카드 목록으로 표시된다": lambda: fexists("frontend", "src", "pages", "Dashboard.jsx"),
    "SummaryCard에 총 지출 / 이번달 지출 금액이 표시된다": lambda: fexists("frontend", "src", "components", "SummaryCard.jsx"),
    "날짜 필터 적용 시 해당 기간 내역만 표시된다": lambda: fexists("frontend", "src", "components", "FilterBar.jsx"),
    "내역이 없을 때 Empty State가 표시된다": lambda: (
        fexists("frontend", "src", "pages", "Dashboard.jsx")
        and fcontains("frontend/src/pages/Dashboard.jsx", "empty")
    ),

    # Phase 7 ─ 상세/수정 화면
    "ExpenseCard 클릭 시 상세 페이지로 이동한다": lambda: fexists("frontend", "src", "components", "ExpenseCard.jsx"),
    '필드 수정 후 "수정 저장" 클릭 시 PUT API가 호출되고 Toast가 표시된다': lambda: fexists("frontend", "src", "components", "EditForm.jsx"),
    '"삭제" 클릭 시 Modal이 열리고': lambda: fexists("frontend", "src", "components", "Modal.jsx"),
}


def update_prd():
    if not os.path.exists(PRD_FILE):
        print(f"[update_prd] PRD 파일 없음: {PRD_FILE}", file=sys.stderr)
        return

    with open(PRD_FILE, encoding="utf-8") as f:
        lines = f.readlines()

    changed = 0
    for i, line in enumerate(lines):
        if "- [ ]" not in line:
            continue
        for keyword, condition_fn in CRITERIA.items():
            if keyword in line and safe_check(condition_fn):
                lines[i] = line.replace("- [ ]", "- [x]", 1)
                changed += 1
                break  # 한 라인에 하나의 기준만 적용

    if changed:
        with open(PRD_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"[update_prd] PRD 업데이트: {changed}개 항목 완료 처리됨")
    else:
        print("[update_prd] 새로 완료된 항목 없음")


if __name__ == "__main__":
    update_prd()
