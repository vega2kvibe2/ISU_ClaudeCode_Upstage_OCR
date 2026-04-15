# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

영수증(JPG/PNG/PDF) 업로드 → Upstage Vision LLM으로 자동 OCR 파싱 → JSON 파일 저장 → 지출 내역 조회·관리하는 경량 웹 앱. DB 미사용, 1일 스프린트 기준으로 설계됨.

---

## 디렉토리 구조

```
receipt-tracker/
├── frontend/          # React 18 + Vite 5 + TailwindCSS 3 + Axios
│   ├── src/
│   │   ├── pages/     # Dashboard, UploadPage, ExpenseDetail
│   │   ├── components/ # Badge, Modal, Toast, DropZone 등 재사용 컴포넌트
│   │   └── api/       # Axios 인스턴스 (baseURL: VITE_API_BASE_URL)
│   ├── package.json
│   └── vite.config.js
├── backend/           # Python FastAPI + LangChain + Upstage
│   ├── main.py        # FastAPI 앱 진입점 + 라우터 등록
│   ├── routers/       # API 라우터 모듈
│   ├── services/      # LangChain + Upstage Vision LLM 오케스트레이션
│   ├── data/
│   │   └── expenses.json  # 지출 데이터 누적 저장 (append 방식)
│   └── requirements.txt
├── images/            # 테스트용 영수증 샘플 이미지 (개발/테스트 전용)
├── vercel.json        # Vercel 라우팅 설정
├── .env               # 로컬 환경변수 (UPSTAGE_API_KEY, GITHUB_API_KEY)
└── PRD_영수증_지출관리앱.md  # 상세 요구사항 문서
```

---

## 개발 명령어

### 백엔드 (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 프론트엔드 (React + Vite)

```bash
cd frontend
npm install
npm run dev        # 개발 서버 (포트 5173)
npm run build      # 프로덕션 빌드
npm run preview    # 빌드 결과 미리보기
```

---

## API 엔드포인트

| 메서드 | URL | 설명 |
|--------|-----|------|
| `POST` | `/api/upload` | 영수증 업로드 및 OCR 파싱 (`multipart/form-data`) |
| `GET` | `/api/expenses` | 전체 지출 내역 조회 (`?from=&to=` 날짜 필터) |
| `DELETE` | `/api/expenses/{id}` | 특정 지출 내역 삭제 |
| `PUT` | `/api/expenses/{id}` | 지출 내역 수정 |
| `GET` | `/api/summary` | 지출 합계 통계 (`?month=`) |

---

## 데이터 구조 (expenses.json 스키마)

```json
{
  "id": "uuid-v4",
  "created_at": "ISO8601",
  "store_name": "string",
  "receipt_date": "YYYY-MM-DD",
  "receipt_time": "HH:MM",
  "category": "string",
  "items": [{ "name": "string", "quantity": 0, "unit_price": 0, "total_price": 0 }],
  "subtotal": 0,
  "discount": 0,
  "tax": 0,
  "total_amount": 0,
  "payment_method": "string",
  "raw_image_path": "uploads/filename"
}
```

---

## 핵심 아키텍처

### OCR 처리 흐름 (백엔드)

```
업로드 파일 → PIL/pdf2image 전처리 → Base64 인코딩
→ LangChain Chain → ChatUpstage Vision LLM (document-digitization-vision)
→ OutputParser (JSON) → expenses.json append 저장
```

### Upstage LLM 연동

- 모델: `solar-pro` 또는 `document-digitization-vision`
- API Key: 환경변수 `UPSTAGE_API_KEY`
- LangChain `ChatUpstage` 클래스 사용
- System Prompt: JSON 형식만 응답하도록 지시

### 데이터 영속성 전략

Vercel 서버리스는 파일시스템이 유지되지 않으므로, 로컬 개발/테스트 외 배포 시 아래 중 하나 선택:
- `localStorage` 병행 저장 (클라이언트 측)
- Railway/Render 배포 (파일시스템 유지)
- Vercel KV (Redis) 또는 Supabase 전환

---

## 환경변수

| 변수명 | 설명 | 위치 |
|--------|------|------|
| `UPSTAGE_API_KEY` | Upstage API 인증 키 | `.env` / Vercel |
| `VITE_API_BASE_URL` | 백엔드 API 기본 URL | Vercel 프론트 빌드 시 주입 |
| `DATA_FILE_PATH` | expenses.json 경로 | Vercel 백엔드 서버리스 |

---

## 테스트 샘플

`images/` 디렉토리에 다양한 영수증 샘플이 있음:
- PNG/JPG: 이마트, 스타벅스, CU, 롯데백화점, 롯데리아, IKEA, 유니클로, CGV, 메가박스, 의료, 택시
- PDF: GS25 편의점 영수증

UI 버그 스크린샷: `images/ui/` — 개발 중 발견된 오류 케이스 참고용

---

## Vercel 배포 설정 (vercel.json)

```json
{
  "builds": [
    { "src": "frontend/package.json", "use": "@vercel/static-build" },
    { "src": "backend/main.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "backend/main.py" },
    { "src": "/(.*)", "dest": "frontend/dist/$1" }
  ]
}
```

---

## 제약사항

- 지원 파일: JPG, PNG, PDF (최대 10MB)
- 한국어·영어 영수증만 지원 (다국어 제외)
- 인증/로그인 없음 (1차 범위 외)
- 단일 사용자 기준 설계
